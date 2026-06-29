#!/usr/bin/env python3
"""
ColabFold MSA 生成脚本
使用 ColabFold API (api.colabfold.com) 生成 MSA 的 .a3m 文件

用法：
    python gen_msa.py -s "MKQLTAS..." -o output.a3m
    python gen_msa.py -f input.fasta -o output.a3m
    python gen_msa.py -s "MKQLTAS..." -o output.a3m -n my_job -p http://127.0.0.1:7897
"""

import time
import os
import tarfile
import io
import requests
import argparse
import sys

def run_colabfold_msa(sequence: str, output_path: str, job_name: str = "colabfold_job", proxy: str = None):
    """
    使用 ColabFold API 对给定序列进行 MSA，并解压保存为 a3m 文件。
    
    :param sequence: 氨基酸序列
    :param output_path: 最终导出的 a3m 文件保存路径
    :param job_name: 任务名称
    :param proxy: 代理地址 (例如: "http://127.0.0.1:7897")
    """
    base_url = "https://api.colabfold.com"
    
    # 设置代理
    proxies = None
    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        print(f"[INFO] 使用代理: {proxy}")
    
    # 1. 提交 MSA 任务
    print("[INFO] 正在提交序列到 ColabFold MSA 服务器...")
    submit_url = f"{base_url}/ticket/msa"
    payload = {
        "q": f">{job_name}\n{sequence}",
        "mode": "mmseqs2"
    }
    
    try:
        response = requests.post(submit_url, data=payload, proxies=proxies, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        
        job_id = res_json.get("id")
        if not job_id:
            print(f"[ERROR] 提交失败，未获取到 Job ID。服务器返回：{res_json}")
            return False
        
        print(f"[INFO] 任务提交成功！Job ID: {job_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        return False

    # 2. 轮询任务状态并等待完成
    status_url = f"{base_url}/ticket/{job_id}"
    max_wait = 600  # 最大等待 600 秒
    waited = 0
    print("[INFO] 等待服务器处理中，每 5 秒检查一次状态...")
    
    while waited < max_wait:
        try:
            status_res = requests.get(status_url, proxies=proxies, timeout=30)
            status_res.raise_for_status()
            status_json = status_res.json()
            status = status_json.get("status")
            
            if status == "COMPLETE":
                print("[INFO] MSA 比对完成！")
                break
            elif status == "ERROR":
                print("[ERROR] 服务器处理出错，请检查序列是否有效。")
                return False
            elif status == "RUNNING" or status == "PENDING":
                waited += 5
                if waited % 30 == 0:
                    print(f"[INFO] 处理中... (已等待 {waited} 秒)")
                time.sleep(5)
            else:
                print(f"[WARN] 未知状态: {status}")
                time.sleep(5)
                waited += 5
        except Exception as e:
            print(f"[WARN] 检查状态时出错: {e}，将在 5 秒后重试...")
            time.sleep(5)
            waited += 5

    if waited >= max_wait:
        print(f"[ERROR] 等待超时（{max_wait} 秒）")
        return False

    # 3. 下载并解压 res.tar.gz 提取 a3m 文件
    download_url = f"{base_url}/result/download/{job_id}"
    print(f"[INFO] 正在从 {download_url} 下载结果压缩包...")
    
    try:
        download_res = requests.get(download_url, proxies=proxies, timeout=120)
        download_res.raise_for_status()
        
        # 将下载的二进制流读入内存并解压
        with tarfile.open(fileobj=io.BytesIO(download_res.content), mode="r:gz") as tar:
            # ColabFold 返回的压缩包里通常包含 uniref.a3m 以及可能包含的 bfd.mgnify...a3m
            # 我们筛选出所有的 .a3m 文件
            a3m_members = [m for m in tar.getmembers() if m.name.endswith(".a3m")]
            
            if not a3m_members:
                print("[ERROR] 压缩包中没有找到 .a3m 格式的 MSA 文件。")
                print(f"[INFO] 压缩包中文件: {[m.name for m in tar.getmembers()]}")
                return False
            
            # 默认提取第一个主要的 a3m 文件（通常是最终比对结果）
            target_member = a3m_members[0]
            print(f"[INFO] 正在解压文件: {target_member.name}")
            
            # 读取文件内容
            a3m_file_bytes = tar.extractfile(target_member).read()
            a3m_text = a3m_file_bytes.decode("utf-8")
            
            # 确保输出目录存在并保存
            output_dir = os.path.dirname(os.path.abspath(output_path))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(a3m_text)
            
            # 统计序列数
            seq_count = a3m_text.count(">")
            print(f"[SUCCESS] MSA 结果已成功保存至: {output_path}")
            print(f"[INFO] 包含 {seq_count} 条序列")
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 下载文件失败: {e}")
        return False
    except tarfile.TarError as e:
        print(f"[ERROR] 解压失败，返回的数据可能不是正确的压缩包: {e}")
        return False


def read_fasta(file_path: str) -> tuple:
    """
    读取 FASTA 文件，返回 (序列名称, 序列)
    """
    seq_name = "sequence"
    sequences = []
    
    with open(file_path, "r") as f:
        current_seq = []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq:
                    sequences.append("".join(current_seq))
                    current_seq = []
                seq_name = line[1:].split()[0]  # 取第一个单词作为名称
            else:
                current_seq.append(line)
        if current_seq:
            sequences.append("".join(current_seq))
    
    if not sequences:
        print("[ERROR] FASTA 文件中没有序列")
        return None, None
    
    if len(sequences) > 1:
        print(f"[WARN] FASTA 文件包含 {len(sequences)} 条序列，只使用第一条")
    
    print(f"[INFO] 从 {file_path} 读取序列: {seq_name}, 长度: {len(sequences[0])}")
    return seq_name, sequences[0]


def main():
    parser = argparse.ArgumentParser(
        description="使用 ColabFold API 生成 MSA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 从命令行直接输入序列
    python gen_msa.py -s "MKQLTASMETYFQ..." -o my_msa.a3m

    # 从 FASTA 文件读取
    python gen_msa.py -f input.fasta -o my_msa.a3m

    # 指定任务名称和代理
    python gen_msa.py -s "MKQLTAS..." -o my_msa.a3m -n my_job -p http://127.0.0.1:7897
        """
    )

    # 输入方式（二选一）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-s", "--sequence", help="氨基酸序列字符串")
    input_group.add_argument("-f", "--fasta", help="FASTA 文件路径")

    # 输出
    parser.add_argument("-o", "--output", default="msa.a3m", help="输出 .a3m 文件路径（默认: msa.a3m）")

    # 任务名称
    parser.add_argument("-n", "--name", default="colabfold_job", help="任务名称（默认: colabfold_job）")

    # 代理
    parser.add_argument("-p", "--proxy", help="HTTP/HTTPS 代理地址，例如 http://127.0.0.1:7897")

    # 超时
    parser.add_argument("--timeout", type=int, default=600, help="最大等待时间（秒，默认: 600）")

    args = parser.parse_args()

    # 获取序列
    if args.fasta:
        seq_name, sequence = read_fasta(args.fasta)
        if sequence is None:
            sys.exit(1)
        job_name = seq_name
    else:
        sequence = args.sequence
        job_name = args.name

    # 如果指定了代理，设置环境变量
    if args.proxy:
        os.environ["http_proxy"] = args.proxy
        os.environ["https_proxy"] = args.proxy
        print(f"[INFO] 设置代理: {args.proxy}")

    # 打印配置信息
    print(f"[INFO] MSA 生成配置:")
    print(f"      序列长度: {len(sequence)}")
    print(f"      任务名称: {job_name}")
    print(f"      输出文件: {args.output}")
    print(f"      最大等待: {args.timeout} 秒")
    print()

    # 运行 MSA
    success = run_colabfold_msa(
        sequence=sequence,
        output_path=args.output,
        job_name=job_name,
        proxy=args.proxy,
    )

    if success:
        print(f"\n[SUCCESS] MSA 生成成功！文件: {args.output}")
        sys.exit(0)
    else:
        print(f"\n[ERROR] MSA 生成失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
