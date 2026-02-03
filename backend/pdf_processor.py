# Triggering fresh build for Hugging Face Spaces
from typing import List, Dict
import pypdf
import io
import os
import requests
import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Takes raw bytes from a PDF file and returns the extracted text.
    Includes an OCR fallback for scanned documents.
    """
    pdf_file = io.BytesIO(file_content)
    pdf_reader = pypdf.PdfReader(pdf_file)
    
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    # OCR Fallback: If no text was found (or very little), it might be a scanned image
    if len(text.strip()) < 100:
        logger.info("Very little text found. Attempting OCR fallback...")
        try:
            from pdf2image import convert_from_bytes
            import easyocr
            import numpy as np

            # 1. Convert PDF to list of PIL Images
            # Note: poppler must be installed on the system (brew install poppler)
            images = convert_from_bytes(file_content)
            
            # 2. Initialize EasyOCR Reader (English)
            reader = easyocr.Reader(['en'])
            
            ocr_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR...")
                # Convert PIL to numpy array for EasyOCR
                img_np = np.array(image)
                # detail=0 returns only the text strings
                result = reader.readtext(img_np, detail=0)
                ocr_text += " ".join(result) + "\n"
            
            if len(ocr_text.strip()) > 0:
                logger.info("OCR extraction successful.")
                return ocr_text
                
        except Exception as e:
            logger.error(f"OCR Fallback failed: {str(e)}")
            
    return text

def create_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 100):
    """
    Splits long text into smaller chunks for the AI to process.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    # This creates a list of 'Document' objects
    chunks = text_splitter.create_documents([text])
    return chunks

from pinecone import Pinecone
import logging
from langchain_core.documents import Document

# Global placeholders
_pc = None
_index = None

def get_pinecone_index():
    """
    Lazy-initializes Pinecone to avoid module-level startup crashes.
    """
    global _pc, _index
    if _pc is None:
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not api_key:
            raise ValueError("CRITICAL: PINECONE_API_KEY is not set in environment variables.")
        if not index_name:
            raise ValueError("CRITICAL: PINECONE_INDEX_NAME is not set in environment variables.")
            
        _pc = Pinecone(api_key=api_key)
        _index = _pc.Index(index_name)
    return _index

def get_embeddings_model():
    """
    Initializes the Hugging Face Embeddings model using the Inference API.
    """
    embeddings = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_KEY")
    )
    return embeddings

async def save_to_pinecone(chunks, doc_id: int):
    """
    Directly upserts vectors to Pinecone avoiding LangChain's broken wrapper.
    """
    embeddings_model = get_embeddings_model()
    index = get_pinecone_index()
    
    # 1. Prepare vectors for upsert
    vectors_to_upsert = []
    
    # Extract texts and generate embeddings in bulk if possible, 
    # but for simplicity and reliability in 3.14, we'll do them in a loop or batches.
    texts = [chunk.page_content for chunk in chunks]
    embeddings = embeddings_model.embed_documents(texts)
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # Create a unique ID for each chunk
        vector_id = f"doc_{doc_id}_chunk_{i}"
        metadata = chunk.metadata.copy()
        metadata["doc_id"] = doc_id
        metadata["text"] = chunk.page_content # We need to store text in metadata to retrieve it
        
        vectors_to_upsert.append({
            "id": vector_id,
            "values": embedding,
            "metadata": metadata
        })
    
    # 2. Upsert to Pinecone
    # Pinecone likes batches of ~100
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i : i + batch_size]
        index.upsert(vectors=batch)
    
    return f"pinecone_{doc_id}"

async def similarity_search(query: str, pdf_ids: List[int], k: int = 3):
    """
    Directly queries Pinecone with metadata filters.
    """
    if not pdf_ids:
        return []
        
    embeddings_model = get_embeddings_model()
    index = get_pinecone_index()
    
    # 1. Generate query embedding
    query_vector = embeddings_model.embed_query(query)
    
    # 2. Create Metadata Filter: (doc_id IN [id1, id2, ...])
    search_filter = {"doc_id": {"$in": pdf_ids}}
    
    # 3. Perform the search
    results = index.query(
        vector=query_vector,
        top_k=k,
        include_metadata=True,
        filter=search_filter
    )
    
    # 4. Reconstruct LangChain Documents from results
    docs = []
    for match in results["matches"]:
        metadata = match["metadata"]
        text = metadata.pop("text", "")
        docs.append(Document(page_content=text, metadata=metadata))
    
    return docs

import logging

# 1. SETUP LOCAL LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("backend.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from langchain_core.language_models.llms import LLM
from typing import Any, List, Optional, Dict

class HFRouterLLM(LLM):
    """
    A Custom LangChain LLM class that talks to the Hugging Face Router.
    This allows us to maintain the "LangChain Way" while avoiding 
    the current bugs in the official integration libraries.
    """
    model_id: str = "meta-llama/Llama-3.2-3B-Instruct"
    api_key: str = os.getenv("HUGGINGFACE_API_KEY")
    temperature: float = 0.1
    max_tokens: int = 512

    @property
    def _llm_type(self) -> str:
        return "hf_router_custom"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Required by LangChain base class."""
        return "Please use ainvoke."

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """The actual Async logic to talk to the AI."""
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(API_URL, headers=headers, json=payload, timeout=60.0)
                if response.status_code != 200:
                    return f"Error from AI ({response.status_code}): {response.text}"
                result = response.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Error connecting to AI: {str(e)}"

async def generate_answer(query: str, context: str):
    """
    Uses the custom HFRouterLLM while keeping the LangChain PromptTemplate.
    """
    llm = HFRouterLLM()
    
    template = """You are a helpful AI assistant for a PDF Q&A system. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer or if the context doesn't contain it, just say that you don't know, don't try to make up an answer.
Keep the answer concise and professional.

Context:
{context}

Question: 
{question}

Answer:"""

    prompt_template = PromptTemplate(template=template, input_variables=["context", "question"])
    formatted_prompt = prompt_template.format(context=context, question=query)
    
    logger.info(f"Generating answer using Custom LangChain LLM (Llama-3.2-3B)")
    answer = await llm.ainvoke(formatted_prompt)
    
    return answer
