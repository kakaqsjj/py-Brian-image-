import os
import shutil
import pydicom
from collections import defaultdict
import time

# ================= 配置区域 =================
# 源文件夹根目录
source_root = r"E:\sjk\RF-TC\new\8902"
# 目标文件夹根目录
target_root = r"E:\sjk\RF-TC\raw8902"


# ===========================================

def sanitize_filename(name):
    """去除文件名中的非法字符"""
    return "".join(c for c in name if c not in r'\/:*?"<>|')


def print_table(data):
    """在控制台打印漂亮的表格"""
    # 定义表头
    headers = ["序号", "患者ID/姓名", "文件数量", "序列数量", "状态"]

    # 计算每列的最大宽度，用于对齐
    widths = [6, 25, 10, 10, 15]

    # 打印分割线
    line = "+" + "+".join(["-" * (w + 2) for w in widths]) + "+"
    print("\n" + line)

    # 打印表头
    header_row = "|"
    for h, w in zip(headers, widths):
        # 中文对齐在控制台比较麻烦，这里简单处理，使用居中或左对齐
        header_row += f" {h:<{w}} |"
    print(header_row)
    print(line)

    # 打印数据行
    for row in data:
        data_str = "|"
        # 序号, 患者名, 文件数, 序列数, 状态
        data_str += f" {str(row[0]):<{widths[0]}} |"
        data_str += f" {str(row[1]):<{widths[1]}} |"
        data_str += f" {str(row[2]):<{widths[2]}} |"
        data_str += f" {str(row[3]):<{widths[3]}} |"
        data_str += f" {str(row[4]):<{widths[4]}} |"
        print(data_str)

    print(line + "\n")


def main():
    # 确保目标根目录存在
    os.makedirs(target_root, exist_ok=True)

    # 获取所有患者文件夹
    patient_list = [p for p in os.listdir(source_root) if os.path.isdir(os.path.join(source_root, p))]

    print(f"检测到 {len(patient_list)} 个患者文件夹，开始逐个处理...\n")

    # 用于存储最终的统计表格数据
    summary_data = []

    # --- 开始逐个患者处理 ---
    for idx, patient_name in enumerate(patient_list, 1):
        patient_src = os.path.join(source_root, patient_name)
        patient_dst = os.path.join(target_root, patient_name)

        print(f"[{idx}/{len(patient_list)}] 正在处理: {patient_name} ... ", end="", flush=True)

        # 初始化该患者的统计数据
        file_count = 0
        series_dict = defaultdict(list)
        status = "成功"

        try:
            # 1. 扫描 DICOM 文件
            for root, _, files in os.walk(patient_src):
                for f in files:
                    if not f.lower().endswith(".dcm"):
                        continue

                    fpath = os.path.join(root, f)
                    try:
                        # 只读头部，不读像素，加快速度
                        ds = pydicom.dcmread(fpath, stop_before_pixels=True)
                        uid = ds.get("SeriesInstanceUID", None)
                        if uid:
                            series_dict[uid].append(fpath)
                            file_count += 1
                    except:
                        # 读取单个文件失败跳过，不影响整体
                        pass

            if file_count == 0:
                status = "无DCM文件"
                print("跳过 (无文件)")
            else:
                # 2. 创建目标文件夹并复制
                os.makedirs(patient_dst, exist_ok=True)

                for uid, flist in series_dict.items():
                    # 获取序列描述用于命名文件夹
                    try:
                        first_dcm = pydicom.dcmread(flist[0], stop_before_pixels=True)
                        series_num = str(first_dcm.get("SeriesNumber", "000"))
                        series_desc = first_dcm.get("SeriesDescription", "Unknown").replace(" ", "_")

                        folder_name = f"{series_num.zfill(3)}-{series_desc}"
                        folder_name = sanitize_filename(folder_name)

                        series_dir = os.path.join(patient_dst, folder_name)
                        os.makedirs(series_dir, exist_ok=True)

                        for src_file in flist:
                            fname = os.path.basename(src_file)
                            dst_file = os.path.join(series_dir, fname)
                            if not os.path.exists(dst_file):
                                shutil.copy2(src_file, dst_file)
                    except Exception as e:
                        print(f"\n    错误: 序列处理失败 {uid} - {e}")
                        status = "部分错误"

                print("完成")

        except Exception as e:
            print(f"失败! 错误信息: {e}")
            status = "处理失败"

        # 记录到统计表 [序号, 患者名, 文件总数, 序列总数, 状态]
        summary_data.append([idx, patient_name, file_count, len(series_dict), status])

    # --- 全部处理完毕，输出表格 ---
    print("\n" + "=" * 30 + " 处理报告 " + "=" * 30)
    print_table(summary_data)
    print(f"结果已保存在: {target_root}")


if __name__ == "__main__":
    main()