# PicoZip

> 零依赖、纯 Python 标准库的**多算法压缩实验室**。亲手实现 RLE、规范 Huffman、LZSS、LZW 以及类 DEFLATE 的 LZSS+Huffman 混合编码，配套 `.pz` 容器（CRC-32 校验）、命令行工具、基准测试与一个暗色 Canvas 可视化工作台。

PicoZip 不是对 `zlib` 的封装——**每一种编解码都从零手写**，用最直白的标准库代码把"数据为什么能被压缩"讲清楚。

## 特性

- **五种真实编解码，全部从零实现**
  - **RLE**：行程编码，`(长度, 字节)`，适合连续字节（图像、零填充）。
  - **Huffman**：频次建最优前缀码，输出**规范码（canonical code）**，末尾用快速查表解码。
  - **LZSS**：4096 字节滑窗、三字节哈希链查找，输出 `literal` 或 `(distance, length)`，支持重叠匹配。
  - **LZW**：12 位动态字典（CLEAR/END 控制码），字典满自动重置，处理经典 `KwKw` 边界。
  - **Hybrid（DEFLATE-lite）**：LZSS token 流再经 Huffman 熵编码，通用文本/源码压缩率最佳。
- **`.pz` 容器**：20 字节大端头（魔数、版本、算法 id、原始长度、CRC-32、载荷长度），解压时校验完整性。
- **Shannon 熵分析**：频次分布、零阶熵（bit/byte）、理论下界。
- **CLI**：`compress / decompress / inspect / entropy / codecs / bench / serve`，支持 `--json`。
- **可视化工作台**：暗色六标签，零构建原生 HTML/CSS/JS，Canvas 绘制 Huffman 建树、LZSS 滑窗、压缩率柱状图，可逐帧播放。
- **完全离线**：`serve` 只绑定 `127.0.0.1`，输入数据不离开本机。
- **零依赖**：仅用 Python 标准库，兼容 Python 3.9–3.13。

## 安装

```bash
git clone https://github.com/18971181532/picozip.git
cd picozip
pip install -e .
```

安装后得到命令 `picozip`（也可用 `python -m picozip.cli`）。

## 命令行用法

```bash
# 列出算法
picozip codecs

# 压缩（默认 hybrid），可指定 -a rle|huffman|lzss|lzw|hybrid
picozip compress data.txt -a hybrid          # 生成 data.txt.pz

# 查看文件头
picozip inspect data.txt.pz

# 字节熵分析
picozip entropy data.txt

# 解压（自动按文件头里的算法选择）
picozip decompress data.txt.pz -o data.out

# 跑内置样本基准（自然语言 / 重复 / 连续 / 随机）
picozip bench
picozip bench data.txt --json
```

一次压缩的输出示例：

```
hybrid: 4.7KB -> data.txt.pz (2.3KB, ratio 0.486)
```

## 可视化工作台

```bash
picozip serve --host 127.0.0.1 --port 8858
```

浏览器打开 http://127.0.0.1:8858/ ，六个标签：

1. **压缩对比**：原始大小、熵、理论下界，五种算法的载荷 / 文件大小 / 压缩率 / 编解码耗时。
2. **Huffman 树**：按合并过程逐帧播放二叉树构建，0/1 分支着色，附频次与码字表。
3. **LZSS 滑窗**：逐 token 播放，高亮滑窗内的源区间与目标区间，直观理解 `(distance,length)`。
4. **LZW 字典**：逐步展示输出码字、短语与字典增长。
5. **基准**：各算法压缩率柱状图，叠加 Shannon 熵下界虚线。
6. **参考**：算法原理、`.pz` 格式、为什么随机数据压缩后反而变大。

## 作为库使用

```python
from picozip import container

data = b"the quick brown fox " * 100

blob = container.pack(data, "hybrid")     # 压缩 + 容器 + CRC
assert container.unpack(blob) == data     # 解压并校验

print(container.inspect(blob))            # 文件头信息
```

直接调用单个算法：

```python
from picozip import huffman, lzss, lzw, hybrid

encoded = huffman.encode(b"abracadabra")
assert huffman.decode(encoded) == b"abracadabra"

payload, tokens = lzss.encode(b"abcabcabc" * 100)
```

## 为什么随机数据压缩后反而变大？

无损压缩是从字节序列到更短字节序列的**一一对应**（鸽巢原理）：不可能让所有输入都变短，必然有一部分输入被编码得更长。随机字节的熵接近 8 bit/byte，不含任何冗余，再加上文件头与码字开销，**任何无损算法都无法缩小它**。PicoZip 会如实展示随机数据上的膨胀，这正是压缩理论的正确行为，而不是 bug。

## `.pz` 容器格式

| 偏移 | 长度 | 字段 |
| ---: | ---: | --- |
| 0 | 2 | 魔数 `PZ` |
| 2 | 1 | 版本（= 1） |
| 3 | 1 | 算法 id（1 RLE / 2 Huffman / 3 LZSS / 4 LZW / 5 Hybrid） |
| 4 | 8 | 原始长度（大端） |
| 12 | 4 | 原始数据 CRC-32 |
| 16 | 4 | 载荷长度（大端） |
| 20 | … | 算法载荷 |

## 目录结构

```
picozip/
├── picozip/
│   ├── __init__.py
│   ├── __main__.py
│   ├── bits.py          # MSB-first 位读写器（整数位偏移 + rewind）
│   ├── varint.py        # LEB128 变长整数
│   ├── entropy.py       # 频次、Shannon 熵、冗余度
│   ├── rle.py           # 行程编码
│   ├── huffman.py       # 规范 Huffman 建码、快速查表解码、树分析
│   ├── lzss.py          # LZ77 滑窗 + 哈希链
│   ├── lzw.py           # 12 位 LZW 字典
│   ├── hybrid.py        # LZSS + Huffman（类 DEFLATE）
│   ├── codecs.py        # 算法注册表
│   ├── container.py     # .pz 容器与 CRC-32
│   ├── bench.py         # 压缩率/耗时基准
│   ├── cli.py           # argparse 命令行
│   ├── server.py        # 本地 HTTP 服务
│   └── web/             # index.html / style.css / app.js
├── tests/               # 11 个测试文件，unittest，含模糊往返与篡改校验
├── examples/
│   └── compress_demo.py
├── .github/workflows/test.yml
├── pyproject.toml
└── LICENSE
```

## 运行测试

```bash
python -m unittest discover -s tests -v
python examples/compress_demo.py
```

## 技术说明

- 全部使用标准库（`heapq` 建 Huffman 树、`zlib.crc32` 算校验、`http.server` 起服务），无第三方依赖。
- Huffman 解码器使用 `2^max_len` 快速查表；位读取器用单一整数位偏移与 `rewind` 处理末尾填充位。
- 代码兼容 Python 3.9+（不使用 `X | Y` 类型联合、`match` 等新语法）。

## License

MIT
