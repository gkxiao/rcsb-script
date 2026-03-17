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

