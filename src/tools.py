#tool1 根据用户id在向量库查询历史体检信息
#tool2 根据用户病史和症状在向量库查询相似病人体检信息
#tool3 根据用户病史和症状在向量库查询疾病相关信息
#tool4 根据用户病史和症状使用浏览器查询疾病相关信息
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from agentos.rag.embedding import EmbeddingModel
from agentos.rag.store import ChromaDB
from config.settings import Config
from agentos.rag.data import merge_content

embedding=EmbeddingModel(
        model_name="BAAI/bge-base-zh-v1.5",
        cache_dir="/mnt/7T/xz"
)

v1=ChromaDB.load_document(
    embedding_model=embedding,
    dir=project_root+Config.VECTORSTORE1_PATH
)

v2=ChromaDB.load_document(
    embedding_model=embedding,
    dir=project_root+Config.VECTORSTORE2_PATH
)



class search_by_id:
    def __init__(self):
        pass

    def run(self,ID:str):
        """
        search_by_id:根据患者id在数据库查询其曾经的体检信息
        Args:
        ID (str): 唯一标识用户的六位数ID
        """
        result = v1.query_data("患者ID:{}".format(ID), query_num=1)
        result = merge_content(result)
        check = result[5:11]
        if check != ID:
            result = "没有找到该患者曾经的的体检信息"
        return result
    


class search_by_other:
    def __init__(self):
        pass

    def run(self,num:int, user_info:str):
        """
        search_by_other:根据患者个人信息在数据库查询相似病人体检信息
        Args:
        num (int): 需要查询的相似体检信息数量(不超过5)
        user_info (str): 用户输入的除ID外全部个人信息，格式为"性别,年龄(岁),身高(cm),体重(kg),既往病史,症状"
        """
        result = v1.query_data(user_info, query_num=int(num))
        result = merge_content(result)
        return result