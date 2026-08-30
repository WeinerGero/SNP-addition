# SNP-addition

Скрипт определяет `REF` и `ALT` для SNP по референсному геному GRCh38.d1.vd1.

## Установка

```bash
git clone https://github.com/WeinerGero/SNP-addition.git
cd SNP-addition

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
python main.py \
    --input FP_SNPs_10k_GB38_twoAllelsFormat.tsv \
    --output result_FP_SNPs_10k_GB38_REF_ALT.tsv
```

Подробное описание:

[FP_SNPs_README.md](https://github.com/WeinerGero/SNP-addition/blob/main/FP_SNPs_README.md)
