# ✅ 用途说明

根据 UniProt accession code 检索 RCSB，返回 PDB code。

---

# ✅ 安装API

```bash
pip install rcsbsearchapi
```

---

# ✅ 使用方法

### 1️⃣ 最简单的例子

```bash
python query_pdb.py -u P00533
```

---

### 2️⃣ 加结构方法筛选

```bash
python query_pdb.py -u P00533 --method "X-RAY DIFFRACTION"
```

---

### 3️⃣ 加分辨率筛选

```bash
python query_pdb.py -u P00533 --method "X-RAY DIFFRACTION" --resolution 3.0
```

---

### 4️⃣ 控制输出数量

```bash
python query_pdb.py -u P00533 --limit 50
```

# ⚠️ 重要提醒

对于像 **EGFR（P00533）**这样的靶标，你会遇到：

* kinase domain vs full-length 混杂
* mutant（T790M 等）
* covalent inhibitor
* inactive/active state

👉 所以：

这个脚本只是 **第一步（数据获取）**
真正关键的是后面的：

```text
structure filtering → pocket alignment → clustering → representative selection
```
