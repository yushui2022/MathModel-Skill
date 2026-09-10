import pandas as pd
import numpy as np
from pathlib import Path

SEARCH_DIRS = ["problem_files", "crawled_data"]
OUTPUT_DIR = Path("paper_output_pro/data_cleaned")
FILE_EXTENSIONS = ["*.csv", "*.xlsx", "*.xls", "*.txt"]

def find_data_files():
    found_files = []
    root_dir = Path.cwd()
    
    for dir_name in SEARCH_DIRS:
        dir_path = root_dir / dir_name
        if not dir_path.exists():
            continue
        
        for ext in FILE_EXTENSIONS:
            files = list(dir_path.rglob(ext))
            for f in files:
                if "paper_output_pro" in str(f) or "node_modules" in str(f) or ".git" in str(f):
                    continue
                if f.name.startswith("~"):
                    continue
                found_files.append(f)
    
    return sorted(list(set(found_files)), key=str)

def clean_dataset(file_path: Path):
    print(f"🔄 正在处理: {file_path.name} ...")
    
    try:
        try:
            if file_path.suffix == '.csv':
                try:
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                    except TypeError:
                        df = pd.read_csv(file_path, encoding='utf-8', error_bad_lines=False)
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file_path, encoding='gbk', on_bad_lines='skip')
                    except TypeError:
                        df = pd.read_csv(file_path, encoding='gbk', error_bad_lines=False)
            elif file_path.suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_path.suffix == '.txt':
                try:
                    try:
                        df = pd.read_csv(file_path, sep=',', on_bad_lines='skip')
                    except TypeError:
                        df = pd.read_csv(file_path, sep=',', error_bad_lines=False)
                except:
                    try:
                        df = pd.read_csv(file_path, sep='\t', on_bad_lines='skip')
                    except TypeError:
                        df = pd.read_csv(file_path, sep='\t', error_bad_lines=False)
            else:
                print(f"⚠️ 不支持的文件格式: {file_path.suffix}")
                return
        except Exception as read_err:
            print(f"⚠️ 读取文件失败 (可能是非结构化文本): {str(read_err)}")
            return

        original_shape = df.shape
        
        df.dropna(how='all', axis=0, inplace=True)
        df.dropna(how='all', axis=1, inplace=True)
        
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    numeric_series = pd.to_numeric(df[col], errors='coerce')
                    if numeric_series.isna().mean() < 0.5:
                        df[col] = numeric_series
                except:
                    pass

        num_cols = df.select_dtypes(include=[np.number]).columns
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        
        for col in num_cols:
            if df[col].isna().any():
                df[col] = df[col].fillna(df[col].mean())
        
        for col in cat_cols:
            if df[col].isna().any():
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val[0])
                else:
                    df[col] = df[col].fillna("Unknown")

        df.drop_duplicates(inplace=True)
        
        cleaned_shape = df.shape
        print(f"✅ 清洗完成: {file_path.name} | 原尺寸 {original_shape} -> 新尺寸 {cleaned_shape}")
        
        output_file = OUTPUT_DIR / f"{file_path.stem}_cleaned.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"💾 已保存至: {output_file}")

    except Exception as e:
        print(f"❌ 处理 {file_path.name} 时出错: {str(e)}")

def main():
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    print("🔍 开始扫描数据文件...")
    files = find_data_files()
    
    if not files:
        print("⚠️ 未找到任何数据文件 (CSV/Excel/TXT)。请确保文件在 problem_files/ 或 crawled_data/ 目录下。")
        return
    
    print(f"📄 找到 {len(files)} 个文件。")
    
    for f in files:
        clean_dataset(f)
        
    print("\n✨ 所有数据清洗任务已完成。")

if __name__ == "__main__":
    main()
