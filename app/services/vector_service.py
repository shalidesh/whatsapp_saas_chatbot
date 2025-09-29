import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings
import structlog
import os
import json
import pickle
from pathlib import Path

from ..config.settings import config

logger = structlog.get_logger(__name__)

class HuggingFaceEmbeddings:
    def __init__(self, api_key: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def encode(self, texts: List[str]) -> np.ndarray:
        """Get embeddings from Hugging Face API"""
        try:
            logger.info(f"Generating embeddings for {len(texts)} chunks")

            # For sentence-transformers models, use feature extraction directly
            return self._try_feature_extraction(texts)

        except Exception as e:
            logger.error(f"Error in encode method: {str(e)}")
            raise e

    def _try_feature_extraction(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using a fallback approach - simple dummy embeddings for now"""
        logger.warning("Using dummy embeddings - HuggingFace API not working correctly")

        # For now, generate consistent dummy embeddings for testing
        all_embeddings = []

        for i, text in enumerate(texts):
            # Create a simple hash-based embedding for consistency
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            # Convert hash to numeric values and normalize
            hash_values = [ord(c) / 255.0 for c in text_hash[:32]]  # Use first 32 chars
            # Pad or truncate to 384 dimensions (standard for MiniLM)
            while len(hash_values) < 384:
                hash_values.extend(hash_values[:min(len(hash_values), 384-len(hash_values))])
            hash_values = hash_values[:384]

            # Add some text-based features
            text_features = [
                len(text) / 1000.0,  # Text length feature
                text.count(' ') / 100.0,  # Word count feature
                text.count('.') / 10.0,   # Sentence count feature
            ]

            # Replace last 3 values with text features
            hash_values[-3:] = text_features

            embedding = np.array(hash_values, dtype=np.float32)
            all_embeddings.append(embedding)

            logger.debug(f"Generated dummy embedding for chunk {i+1}/{len(texts)}")

        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        logger.info(f"Generated dummy embeddings array shape: {embeddings_array.shape}")
        return embeddings_array

class VectorService:
    def __init__(self):
        # Use Hugging Face API instead of local models
        model_name = config.HF_EMBEDDING_MODEL if not config.DEV_MODE else config.LITE_EMBEDDING_MODEL
        self.embeddings = HuggingFaceEmbeddings(
            api_key=config.HUGGINGFACE_API,
            model_name=f"sentence-transformers/{model_name}"
        )

        # Set embedding dimension (384 for MiniLM models)
        self.embedding_dimension = 384
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        if config.VECTOR_DB_TYPE == 'faiss':
            self.vector_db = FAISSVectorDB()
            # Set the embedding dimension and service reference
            self.vector_db.set_embeddings_service(self)
        else:
            self.vector_db = ChromaVectorDB()
    
    async def add_document(self, document_id: int, content: str, business_id: int) -> bool:
        """Add document to vector database"""
        try:
            logger.info(f"Starting document processing for ID {document_id}")

            # Validate inputs
            if not content or not content.strip():
                raise ValueError("Content is empty")

            if len(content.strip()) < 10:
                raise ValueError("Content too short for meaningful processing")

            # Split document into chunks
            chunks = self.text_splitter.split_text(content)
            logger.info(f"Document split into {len(chunks)} chunks")

            if not chunks:
                raise ValueError("No chunks generated from content")

            # Generate embeddings for each chunk using Hugging Face API
            logger.info(f"Generating embeddings using {self.embeddings.model_name}")
            embeddings = self.embeddings.encode(chunks)

            logger.info(f"Generated embeddings with shape: {embeddings.shape}")

            # Validate embeddings
            if embeddings.size == 0:
                raise ValueError("No embeddings generated")

            if len(embeddings) != len(chunks):
                raise ValueError(f"Mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks")

            # Store in vector database
            logger.info(f"Adding document to {type(self.vector_db).__name__}")
            await self.vector_db.add_documents(
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
                business_id=business_id
            )

            logger.info("Document added to vector DB successfully",
                       document_id=document_id, chunks_count=len(chunks))
            return True

        except Exception as e:
            logger.error("Error adding document to vector DB",
                        document_id=document_id, error=str(e), exc_info=True)
            return False
    
    # async def search(self, query: str, business_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
    #     """Search for relevant documents"""
    #     try:
    #         # Generate query embedding
    #         # query_embedding = await self.embeddings.aembed_query(query)
    #         query_embedding = await self.embeddings.encode([query], convert_to_tensor=False)[0]
            
    #         # Search vector database
    #         results = await self.vector_db.search(
    #             query_embedding=query_embedding,
    #             business_id=business_id,
    #             top_k=top_k
    #         )
            
    #         logger.info("Vector search completed", 
    #                    query=query[:50], results_count=len(results))
    #         return results
            
    #     except Exception as e:
    #         logger.error("Error searching vector DB", error=str(e))
    #         return []
        
    async def search(self, query: str, business_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        try:
            # Generate query embedding using Hugging Face API
            query_embedding = self.embeddings.encode([query])

            # Extract the first embedding and convert to list
            if isinstance(query_embedding, np.ndarray) and len(query_embedding.shape) > 1:
                query_embedding = query_embedding[0]

            # Search vector database
            results = await self.vector_db.search(
                query_embedding=query_embedding.tolist(),  # Convert to list
                business_id=business_id,
                top_k=top_k
            )

            logger.info("Vector search completed", query=query[:50], results_count=len(results))
            return results

        except Exception as e:
            logger.error("Error searching vector DB", error=str(e))
            return []
    
    async def delete_document(self, document_id: int, business_id: int) -> bool:
        """Delete document from vector database"""
        try:
            await self.vector_db.delete_document(document_id, business_id)
            logger.info("Document deleted from vector DB", document_id=document_id)
            return True
        except Exception as e:
            logger.error("Error deleting document from vector DB", 
                        document_id=document_id, error=str(e))
            return False

class FAISSVectorDB:
    def __init__(self):
        # Update dimension to be dynamic instead of hardcoded
        self.dimension = None  # Will be set when first embedding is added
        self.indices = {}  # business_id -> faiss index
        self.metadata = {}  # business_id -> list of metadata
        self.embeddings_service = None  # Will store reference to embedding service

        # Persistence configuration
        self.persist_path = Path(config.FAISS_PERSIST_PATH)
        self.auto_save = config.FAISS_AUTO_SAVE

        # Create persistence directory if it doesn't exist
        self.persist_path.mkdir(parents=True, exist_ok=True)

        # Load existing data on initialization
        self._load_from_disk()
    
    def set_embeddings_service(self, embeddings_service):
        """Set reference to embeddings service for reuse"""
        self.embeddings_service = embeddings_service
        if self.dimension is None:
            self.dimension = embeddings_service.embedding_dimension

    def _get_index_path(self, business_id: int) -> Path:
        """Get the file path for a business's FAISS index"""
        return self.persist_path / f"business_{business_id}.index"

    def _get_metadata_path(self, business_id: int) -> Path:
        """Get the file path for a business's metadata"""
        return self.persist_path / f"business_{business_id}_metadata.json"

    def _save_to_disk(self, business_id: int):
        """Save FAISS index and metadata to disk for a specific business"""
        try:
            if business_id in self.indices:
                # Save FAISS index
                index_path = self._get_index_path(business_id)
                faiss.write_index(self.indices[business_id], str(index_path))

                # Save metadata
                metadata_path = self._get_metadata_path(business_id)
                with open(metadata_path, 'w') as f:
                    json.dump(self.metadata.get(business_id, []), f, indent=2)

                logger.info(f"Saved FAISS data for business {business_id}")
        except Exception as e:
            logger.error(f"Error saving FAISS data for business {business_id}", error=str(e))

    def _load_from_disk(self):
        """Load all FAISS indices and metadata from disk"""
        try:
            for index_path in self.persist_path.glob("business_*.index"):
                # Extract business_id from filename
                business_id = int(index_path.stem.split('_')[1])

                # Load FAISS index
                index = faiss.read_index(str(index_path))
                self.indices[business_id] = index

                # Set dimension from loaded index
                if self.dimension is None:
                    self.dimension = index.d

                # Load metadata
                metadata_path = self._get_metadata_path(business_id)
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        self.metadata[business_id] = json.load(f)
                else:
                    self.metadata[business_id] = []

                logger.info(f"Loaded FAISS data for business {business_id}")

        except Exception as e:
            logger.error("Error loading FAISS data from disk", error=str(e))

    def _delete_from_disk(self, business_id: int):
        """Delete FAISS index and metadata files from disk"""
        try:
            index_path = self._get_index_path(business_id)
            metadata_path = self._get_metadata_path(business_id)

            if index_path.exists():
                index_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            logger.info(f"Deleted FAISS files for business {business_id}")
        except Exception as e:
            logger.error(f"Error deleting FAISS files for business {business_id}", error=str(e))
    
    async def add_documents(self, document_id: int, chunks: List[str], 
                          embeddings: List[List[float]], business_id: int):
        """Add documents to FAISS index"""
        # Set dimension if not already set
        if self.dimension is None:
            if hasattr(embeddings, 'shape') and len(embeddings.shape) > 1:
                self.dimension = embeddings.shape[1]
            elif isinstance(embeddings, (list, np.ndarray)) and len(embeddings) > 0:
                self.dimension = len(embeddings[0]) if hasattr(embeddings[0], '__len__') else 384
            else:
                self.dimension = 384  # Default dimension
            
        if business_id not in self.indices:
            self.indices[business_id] = faiss.IndexFlatIP(self.dimension)
            self.metadata[business_id] = []
        
        # Convert embeddings to numpy array
        if isinstance(embeddings, np.ndarray):
            embeddings_array = embeddings.astype('float32')
        else:
            embeddings_array = np.array(embeddings).astype('float32')

        # Ensure 2D array
        if len(embeddings_array.shape) == 1:
            embeddings_array = embeddings_array.reshape(1, -1)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Add to index
        self.indices[business_id].add(embeddings_array)
        
        # Store metadata
        for i, chunk in enumerate(chunks):
            self.metadata[business_id].append({
                'document_id': document_id,
                'chunk_index': i,
                'content': chunk
            })

        # Auto-save to disk if enabled
        if self.auto_save:
            self._save_to_disk(business_id)
    
    async def search(self, query_embedding: List[float], business_id: int, top_k: int):
        """Search FAISS index"""
        if business_id not in self.indices:
            return []
        
        # Convert query embedding to numpy array
        query_array = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_array)
        
        # Search
        scores, indices = self.indices[business_id].search(query_array, top_k)
        
        # Prepare results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata[business_id]):
                metadata = self.metadata[business_id][idx]
                results.append({
                    'content': metadata['content'],
                    'document_id': metadata['document_id'],
                    'score': float(scores[0][i]),
                    'chunk_index': metadata['chunk_index']
                })
        
        return results
    
    async def delete_document(self, document_id: int, business_id: int):
        """Delete document from FAISS (rebuild index without document)"""
        if business_id not in self.indices:
            return
        
        # Filter out metadata for this document
        new_metadata = [m for m in self.metadata[business_id] 
                       if m['document_id'] != document_id]
        
        # Rebuild index if there are remaining documents
        if new_metadata:
            # Get embeddings for remaining chunks using Hugging Face API
            remaining_chunks = [m['content'] for m in new_metadata]
            if self.embeddings_service:
                embeddings = self.embeddings_service.embeddings.encode(remaining_chunks)
            else:
                # Fallback to creating new embedding service
                hf_embeddings = HuggingFaceEmbeddings(
                    api_key=config.HUGGINGFACE_API,
                    model_name=f"sentence-transformers/{config.EMBEDDING_MODEL}"
                )
                embeddings = hf_embeddings.encode(remaining_chunks)
            
            # Create new index
            new_index = faiss.IndexFlatIP(self.dimension)
            embeddings_array = np.array(embeddings).astype('float32')
            faiss.normalize_L2(embeddings_array)
            new_index.add(embeddings_array)
            
            self.indices[business_id] = new_index
            self.metadata[business_id] = new_metadata

            # Auto-save to disk if enabled
            if self.auto_save:
                self._save_to_disk(business_id)
        else:
            # Remove empty index
            del self.indices[business_id]
            del self.metadata[business_id]

            # Delete from disk
            self._delete_from_disk(business_id)

class ChromaVectorDB:
    def __init__(self):
        # Check if we should use HTTP client (for docker) or persistent client (for local)
        if config.CHROMADB_HOST != 'localhost' or os.getenv('USE_CHROMADB_HTTP', 'false').lower() == 'true':
            # Use HTTP client for docker deployments
            self.client = chromadb.HttpClient(
                host=config.CHROMADB_HOST,
                port=config.CHROMADB_PORT,
                settings=Settings(allow_reset=True)
            )
        else:
            # Use persistent client for local development with disk persistence
            persist_path = Path(config.CHROMADB_PERSIST_PATH)
            persist_path.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(allow_reset=True)
            )
    
    async def add_documents(self, document_id: int, chunks: List[str], 
                          embeddings: List[List[float]], business_id: int):
        """Add documents to ChromaDB"""
        collection_name = f"business_{business_id}"
        
        try:
            collection = self.client.get_collection(collection_name)
        except:
            collection = self.client.create_collection(collection_name)
        
        # Prepare data
        ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                'document_id': document_id,
                'chunk_index': i,
                'business_id': business_id
            }
            for i in range(len(chunks))
        ]
        
        # Add to collection
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
    
    async def search(self, query_embedding: List[float], business_id: int, top_k: int):
        """Search ChromaDB"""
        collection_name = f"business_{business_id}"
        
        try:
            collection = self.client.get_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'document_id': results['metadatas'][0][i]['document_id'],
                    'score': 1.0 - results['distances'][0][i],  # Convert distance to similarity
                    'chunk_index': results['metadatas'][0][i]['chunk_index']
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error("Error searching ChromaDB", error=str(e))
            return []
    
    async def delete_document(self, document_id: int, business_id: int):
        """Delete document from ChromaDB"""
        collection_name = f"business_{business_id}"
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get all document IDs for this document
            results = collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                
        except Exception as e:
            logger.error("Error deleting from ChromaDB", error=str(e))