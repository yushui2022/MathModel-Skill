import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import platform

INPUT_DIR = Path("paper_output_pro/data_cleaned")
OUTPUT_DIR = Path("paper_output_pro/figures")

def set_chinese_font():
    """设置 Matplotlib 中文字体，兼容 Windows/Mac/Linux"""
    system = platform.system()
    fonts = []
    
    if system == 'Windows':
        fonts = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'FangSong']
    elif system == 'Darwin':
        fonts = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC']
    else:
        fonts = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']
        
    for font in fonts:
        try:
            plt.rcParams['font.sans-serif'] = [font]
            fig = plt.figure()
            plt.text(0.5, 0.5, '测试')
            plt.close(fig)
            print(f"🔤 已启用中文字体: {font}")
            plt.rcParams['axes.unicode_minus'] = False
            return
        except:
            continue
    print("⚠️ 未找到合适的中文字体，图表中文可能显示为乱码。")

def visualize_dataset(file_path: Path):
    print(f"📊 正在可视化: {file_path.name} ...")
    
    try:
        df = pd.read_csv(file_path)
        
        dataset_output_dir = OUTPUT_DIR / file_path.stem
        dataset_output_dir.mkdir(parents=True, exist_ok=True)
        
        num_cols = df.select_dtypes(include=[np.number]).columns
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        
        MAX_COLS = 20
        for i, col in enumerate(num_cols):
            if i >= MAX_COLS:
                break
            plt.figure(figsize=(10, 6))
            sns.histplot(df[col], kde=True, bins=30)
            plt.title(f"{col} 分布图")
            plt.xlabel(col)
            plt.ylabel("频数")
            plt.tight_layout()
            plt.savefig(dataset_output_dir / f"dist_{i}_{col}.png", dpi=300)
            plt.close()
            
        if len(num_cols) > 1:
            plt.figure(figsize=(12, 10))
            corr = df[num_cols].corr()
            mask = np.triu(np.ones_like(corr, dtype=bool))
            sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap='coolwarm', 
                        linewidths=0.5, square=True, cbar_kws={"shrink": .5})
            plt.title("变量相关性热力图")
            plt.tight_layout()
            plt.savefig(dataset_output_dir / "correlation_heatmap.png", dpi=300)
            plt.close()
            
        if len(num_cols) > 1:
            variances = df[num_cols].var()
            top_cols = variances.nlargest(5).index.tolist()
            
            if len(top_cols) > 1:
                plt.figure()
                sns.pairplot(df[top_cols], kind='scatter', diag_kind='kde', plot_kws={'alpha': 0.6})
                plt.savefig(dataset_output_dir / "pairplot_top5.png", dpi=300)
                plt.close()
        
        for i, col in enumerate(cat_cols):
            if i >= MAX_COLS:
                break
            if df[col].nunique() > 50:
                continue
                
            plt.figure(figsize=(10, 6))
            val_counts = df[col].value_counts().nlargest(20)
            sns.barplot(x=val_counts.index, y=val_counts.values)
            plt.title(f"{col} 频数统计 (Top 20)")
            plt.xlabel(col)
            plt.ylabel("频数")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(dataset_output_dir / f"cat_{i}_{col}.png", dpi=300)
            plt.close()

        print(f"✅ 可视化完成: 已保存至 {dataset_output_dir}")

    except Exception as e:
        print(f"❌ 可视化 {file_path.name} 时出错: {str(e)}")

def main():
    if not INPUT_DIR.exists():
        print(f"⚠️ 找不到清洗后的数据目录: {INPUT_DIR}")
        print("请先运行数据清洗脚本 (clean_data.py)。")
        return
        
    files = list(INPUT_DIR.glob("*.csv"))
    
    if not files:
        print(f"⚠️ {INPUT_DIR} 下没有 CSV 文件。")
        return
        
    set_chinese_font()
    sns.set_theme(style="whitegrid")
    set_chinese_font()
    
    print(f"📄 找到 {len(files)} 个已清洗的数据文件。")
    
    for f in files:
        visualize_dataset(f)
        
    print("\n✨ 所有可视化任务已完成。")

if __name__ == "__main__":
    main()
