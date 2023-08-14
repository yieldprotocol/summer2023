from langchain.vectorstores import ElasticKnnSearch
from langchain.embeddings import HuggingFaceEmbeddings
from pathlib import Path
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
load_dotenv()


MODEL_ID = os.getenv('MODEL_ID') # this is to embed user query to perform hybrid search in Elastic vector db
MODEL_HF_ID = os.getenv('MODEL_HF_ID') # this is just to create the KNNSearch object
INDEX_NAME = os.getenv('INDEX_NAME')
QUERY_BOOST = 15
KNN_BOOST = 5
K_SEARCH = 5 # select top K_SEARCH document chunks based on hybrid search criteria
K_RETURN = 3 # retyrn top K_RETURN document chunks based on our actual need (context, token_limit, etc)
# assert K_RETURN <= K_SEARCH

def get_elastic():
    # Now we'll load these into the python environment
    global es
    if 'es' not in globals():
        es_cloud_id = os.getenv('ES_CLOUD_ID')
        endpoint = os.getenv('ES_ENDPOINT')
        es_user = os.getenv('ES_USER')
        es_pass = os.getenv('ES_PWD')
        es_url =  f"https://{es_user}:{es_pass}@{endpoint}:443"
        es = Elasticsearch(cloud_id=es_cloud_id, basic_auth=(es_user, es_pass))
    return es

def search_question(query_text):
    es = get_elastic() 
    # Elasticsearch query (BM25) and kNN configuration for hybrid search
    print("Query text is", query_text)
    query = {
        "bool": {
            "must": [{
                "match": {
                    "text": {
                        "query": query_text,
                        "boost": QUERY_BOOST
                    }
                }
            }]
        }
    }

    knn = {
        "field": "title-vector",
        "k": K_SEARCH,
        "num_candidates": 20,
        "query_vector_builder": {
            "text_embedding": {
                "model_id": MODEL_ID,
                "model_text": query_text
            }
        },
        "boost": KNN_BOOST
    } # boost is defining relative importance of keyword search and kNN vector retrieval search.

    fields = ["text"] # define the field in document collection to match against query.
    index = INDEX_NAME
    resp = es.search(index=index,
                     query=query,
                     knn=knn,
                     fields=fields,
                     size=K_RETURN,
                     source=True)
    
    # print("Query is", query)
    # print("Response is",resp)
    body = [resp['hits']['hits'][i]['fields']['text'][0] for i in range(len(resp['hits']['hits']))] # return all relevant docs here
    return body