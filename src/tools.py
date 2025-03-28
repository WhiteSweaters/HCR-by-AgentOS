#tool1 根据用户id在向量库查询历史体检信息
#tool2 根据用户病史和症状在向量库查询相似病人体检信息
#tool3 根据用户病史和症状在向量库查询疾病相关信息
#tool4 根据用户病史和症状使用浏览器查询疾病相关信息



class tool1:
    def __init__(self):
        pass

    def run(self,id:str):
        """
        tool1:根据用户id在向量库查询历史体检信息
        Args:
        id (str): 唯一标识用户的id
        """
        result = "查询过血常规，高血压三项"
        return result
    