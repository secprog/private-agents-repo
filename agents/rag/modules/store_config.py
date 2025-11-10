import os
import logging
from langchain_openai import AzureChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
import neo4j


if os.getenv("BYPASS_TOKENIZER", "true").lower() == "true":
    # Disable tiktoken for Azure OpenAI if BYPASS_TOKENIZER is set to true
    from src.agent.custom_emb import AzureOpenAIEmbeddings
else:
    # Use the default Azure OpenAI Embeddings with tiktoken enabled
    from langchain_openai.embeddings import AzureOpenAIEmbeddings


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required environment variables
required_vars = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE",
                 "ENDPOINT", "AZURE_OPENAI_EMBEDDINGS_MODEL_NAME", "AZURE_OPENAI_API_KEY",
                 "AZURE_OPENAI_DEPLOYMENT_NAME", "API_VERSION"]
                 
for var in required_vars:
    if not os.getenv(var):
        logger.warning(f"Environment variable {var} is not set!")

# Define Neo4j store classes
class Neo4jGraphStore:
    """Neo4j graph store for retrieving data using Cypher queries."""
    
    def __init__(self, uri, user, password, database):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.conn = Neo4jGraph(
            url=uri,
            username=user,
            password=password,
            database=database
        )
        logger.info(f"Neo4jGraphStore initialized with database: {database}")
    
    def query(self, cypher, params=None):
        """Execute a Cypher query and return results."""
        try:
            return self.conn.query(cypher, params=params or {})
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return []
    
    def get_schema(self):
        """Get the database schema."""
        try:
            return self.conn.schema
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return ""


class Neo4jVectorStore:
    """Neo4j vector store for embedding-based retrieval."""
    
    def __init__(self, uri, user, password, database, embedding_model):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.conn = Neo4jGraph(
            url=uri,
            username=user,
            password=password,
            database=database
        )
        self._embedding = embedding_model
        logger.info(f"Neo4jVectorStore initialized with database: {database}")
    
    def query(self, cypher, params=None):
        """Execute a Cypher query and return results."""
        try:
            return self.conn.query(cypher, params=params or {})
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return []
    
    def get_documents_by_similarity(self, query, top_k=10):
        """Get documents similar to the query."""
        try:
            embedding = self._embedding.embed_query(query)
            cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding) 
            YIELD node, score RETURN node.id AS id, node.text AS text, score
            """
            return self.query(cypher, {"k": top_k, "embedding": embedding})
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []


# Create connection parameters
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE")

# Create embeddings model
try:
    azure_embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("ENDPOINT"),
        model=os.getenv("AZURE_OPENAI_EMBEDDINGS_MODEL_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )
    logger.info("Azure OpenAI Embeddings model initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize embeddings: {e}")
    azure_embeddings = None

# Initialize stores with error handling
try:
    graph_store = Neo4jGraphStore(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database,
    )
    logger.info("Neo4j Graph Store initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize graph store: {e}")
    graph_store = None

try:
    vector_store = Neo4jVectorStore(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database,
        embedding_model=azure_embeddings,
    )
    logger.info("Neo4j Vector Store initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize vector store: {e}")
    vector_store = None

# Initialize LLM with error handling
try:
    llm = AzureChatOpenAI(
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        azure_endpoint=os.getenv("ENDPOINT"),
        api_version=os.getenv("API_VERSION"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        temperature=0,
    )
    logger.info("Azure OpenAI Chat model initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None

# Add a function to test connectivity
def test_connections():
    """Test all connections and return status."""
    status = {
        "graph_store": False,
        "vector_store": False,
        "llm": False
    }
    
    # Test graph store
    if graph_store:
        try:
            schema = graph_store.get_schema()
            status["graph_store"] = True
            logger.info(f"Graph store schema retrieved: {schema[:100]}...")
        except Exception as e:
            logger.error(f"Graph store test failed: {e}")
    
    # Test vector store
    if vector_store and azure_embeddings:
        try:
            test_query = "This is a test query"
            results = vector_store.get_documents_by_similarity(test_query, top_k=1)
            status["vector_store"] = True
            logger.info(f"Vector store test completed with {len(results)} results")
        except Exception as e:
            logger.error(f"Vector store test failed: {e}")
    
    # Test LLM
    if llm:
        try:
            status["llm"] = True
            logger.info("LLM initialized (not tested with query)")
        except Exception as e:
            logger.error(f"LLM test failed: {e}")
    
    return status