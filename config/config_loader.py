import os
import json
from typing import Dict, List, Optional

class ConfigLoader:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
    
    def load_config(self, project_name: str) -> Optional[Dict]:
        """加载指定项目的配置"""
        config_file = os.path.join(self.config_dir, f"{project_name}.json")
        if not os.path.exists(config_file):
            return None
            
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}")
            return None
    
    def list_configs(self) -> List[Dict]:
        """列出所有已保存的配置"""
        configs = []
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    config = self.load_config(filename[:-5])
                    if config:
                        configs.append(config)
        except Exception as e:
            print(f"列出配置文件时出错: {str(e)}")
        return configs
    
    def delete_config(self, project_name: str) -> bool:
        """删除指定项目的配置"""
        config_file = os.path.join(self.config_dir, f"{project_name}.json")
        if not os.path.exists(config_file):
            return False
            
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            os.remove(config_file)
            return True
        except Exception as e:
            print(f"删除配置文件时出错: {str(e)}")
            return False