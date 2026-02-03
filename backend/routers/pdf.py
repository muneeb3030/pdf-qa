from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
import sys
import os
import io

# Ensure the parent directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models, schemas, auth, database, pdf_processor
from database import get_db
import shutil

router = APIRouter(
    tags=["PDF Processing"]
)

# We define this here so the /upload-pdf route knows how to find the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...), 
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # 1. Strict Validation
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    # Check File Size
    # Note: UploadFile size might not be available until read, but we can check if it exists
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File is too large ({file_size / 1024 / 1024:.1f}MB). Maximum allowed size is 20MB."
        )

    # Check File Extension for friendly errors
    filename = file.filename.lower()
    if filename.endswith(('.docx', '.doc')):
        raise HTTPException(status_code=400, detail="MS Word files are not supported yet. Please upload a PDF.")
    if filename.endswith(('.txt', '.rtf')):
        raise HTTPException(status_code=400, detail="Text files are not supported. Please upload a PDF.")
    
    if not filename.endswith('.pdf') or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF file.")

    # 2. Extract User (Security Check)
    try:
        from jose import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # 3. Read and Extract Text
    pdf_content = await file.read()
    text = pdf_processor.extract_text_from_pdf(pdf_content)

    # 4. Create Chunks
    chunks = pdf_processor.create_chunks(text)

    # 5. Create a record in DB first to get a unique ID
    new_doc = models.Document(
        filename=file.filename,
        vector_path="pending", # Will update in a second
        user_id=user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 6. Save chunks into Pinecone (Cloud)
    # We pass the doc ID for metadata filtering
    await pdf_processor.save_to_pinecone(chunks, new_doc.id)

    # 7. Update the DB with a status flag (path is now virtual 'pinecone')
    new_doc.vector_path = f"pinecone_{new_doc.id}"
    db.commit()

    return {
        "id": new_doc.id,
        "filename": new_doc.filename,
        "status": "success - isolated index created"
    }

@router.get("/documents", response_model=list[schemas.Document])
async def get_documents(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        from jose import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
        return user.documents
    except Exception:
        raise HTTPException(status_code=401, detail="Could not retrieve documents")

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # 1. Get User
    try:
        from jose import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")

    # 2. Find Document and check ownership
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == user.id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    # 3. Delete Physical FAISS Index
    # 3. Delete from Pinecone
    try:
        # Connect to index
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
        # Delete vectors where doc_id matches
        # Note: This is an expensive operation on some Pinecone tiers, 
        # but the correct way for metadata filtering.
        index.delete(filter={"doc_id": {"$eq": doc_id}})
        print(f"Deleted vectors for doc_id: {doc_id}")
    except Exception as e:
        print(f"Error deleting Pinecone vectors: {e}")

    # 4. Delete Database Record
    db.delete(doc)
    db.commit()

    return {"status": "success", "message": f"Document {doc_id} deleted"}

@router.post("/ask")
async def ask_question(
    query: schemas.QuestionMulti,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # 1. Get User
    try:
        from jose import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")

    # 2. Map IDs to Paths (and check ownership)
    docs = db.query(models.Document).filter(
        models.Document.id.in_(query.pdf_ids),
        models.Document.user_id == user.id
    ).all()
    
    if not docs:
        raise HTTPException(status_code=404, detail="No selected documents found or access denied")

    # 3. Similarity Search (Retrieval across multiple IDs using Pinecone metadata filter)
    relevant_docs = await pdf_processor.similarity_search(query.question, query.pdf_ids)
    
    # 4. Combine context
    context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    # 5. Generate Answer
    ai_answer = await pdf_processor.generate_answer(query.question, context_text)
    
    return {
        "question": query.question,
        "answer": ai_answer,
        "sources": [doc.page_content[:100] + "..." for doc in relevant_docs],
        "active_docs": [d.filename for d in docs]
    }
