from src.phoenix.Controller import PhoenixController
import ast
import utils
    

def load_obj(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return utils.preprocess_naming(cluster_state)


if __name__ == "__main__":
    state = load_obj("cluster_env.json")
    controller = PhoenixController(state)
    controller.run()