"""
美股期权卖方推荐工具
US Options Selling Recommendation Tool
"""
import os

def create_project_structure():
    """创建项目目录结构"""
    directories = [
        'src',
        'src/data_collector',
        'src/option_analytics',
        'src/screening',
        'src/risk_management',
        'src/visualization',
        'src/utils',
        'tests',
        'examples',
        'data',
        'data/cache',
        'data/output',
        'config'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # 创建__init__.py文件
    init_files = [
        'src/__init__.py',
        'src/data_collector/__init__.py',
        'src/option_analytics/__init__.py',
        'src/screening/__init__.py',
        'src/risk_management/__init__.py',
        'src/visualization/__init__.py',
        'src/utils/__init__.py'
    ]
    
    for init_file in init_files:
        with open(init_file, 'w') as f:
            f.write('')
        print(f"Created file: {init_file}")

if __name__ == "__main__":
    create_project_structure()
    print("Project structure created successfully!")