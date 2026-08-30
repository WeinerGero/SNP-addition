# SNP-addition

![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![Samtools](https://img.shields.io/badge/Samtools-1.24-4EAA25)

Скрипт определяет `REF` и `ALT` для SNP из GRAF 2.4 по референсному геному GRCh38.d1.vd1.

Входной формат:

```text
#CHROM    POS    ID    allele1    allele2
```

Выходной формат:

```text
#CHROM    POS    ID    REF    ALT
```

Если референсный нуклеотид совпадает с `allele1` или `allele2`, записываю его в `REF`, второй аллель в `ALT`. Если совпадения нет, SNP сохраняется в `unrecognized_SNPs.tsv`.

## 1. Клонирование и окружение

Клонирую репозиторий, создаю окружение Python 3.10 и устанавливаю зависимости.

```bash
git clone https://github.com/WeinerGero/SNP-addition.git /content/SNP-addition
cd /content/SNP-addition

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Предобработка FP_SNPs.txt

Перед запуском Python-скрипта оставляю координаты GRCh38, меняю порядок колонок, добавляю `chr` и `rs`, исключаю варианты X-хромосомы с номером `23`.

```bash
# скачивает GRAF 2.4 и распаковывает данные
# формирует FP_SNPs_10k_GB38_twoAllelsFormat.tsv
# сохраняет исходный FP_SNPs.txt

curl -L http://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/GetZip.cgi?zip_name=GRAF_files.zip \
  | tar -zxf - -C /tmp/ \
  && awk -F'\t' 'BEGIN {OFS="\t"} \
      NR==1 { print "#CHROM", "POS", "ID", "allele1", "allele2"; next } \
      { if ($2 == "23") { next }; print "chr"$2, $4, "rs"$1, $5, $6 }' \
      /tmp/data/FP_SNPs.txt > /content/SNP-addition/FP_SNPs_10k_GB38_twoAllelsFormat.tsv \
  && cp /tmp/data/FP_SNPs.txt /content/SNP-addition/FP_SNPs.txt \
  && rm -rf /tmp/data
```

Получаю `FP_SNPs_10k_GB38_twoAllelsFormat.tsv` с 10 000 аутосомных SNP.

## 3. Подготовка Samtools 1.24

Samtools использую для разделения и индексирования GRCh38.d1.vd1.

```bash
# устанавливает зависимости для сборки
apt-get update -qq
apt-get install -y build-essential zlib1g-dev libbz2-dev liblzma-dev libncurses-dev

# скачивает и собирает Samtools 1.24
curl -L https://github.com/samtools/samtools/releases/download/1.24/samtools-1.24.tar.bz2 \
  | tar -xj -C /tmp

cd /tmp/samtools-1.24 && \
  ./configure --prefix=/content/samtools-1.24 && \
  make -j"$(nproc)" && \
  make install
```

## 4. Подготовка GRCh38.d1.vd1

Скачиваю референсный геном и сохраняю подготовленные файлы на хостовой машине в каталоге из ТЗ:

```text
/mnt/data/ref/GRCh38.d1.vd1_mainChr/sepChrs/
```

```bash
# скачивает и распаковывает GRCh38.d1.vd1
curl -L \
    -o /tmp/gdc_data.tar.gz \
    https://api.gdc.cancer.gov/data/254f697d-310d-4d7d-a27b-27fbf767a834 \
    && mkdir -p /tmp/gdc_data \
    && tar -xzf /tmp/gdc_data.tar.gz -C /tmp/gdc_data

# формирует chr*.fa и индексы chr*.fa.fai
REF_DIR=/mnt/data/ref/GRCh38.d1.vd1_mainChr/sepChrs
SAMTOOLS=/content/samtools-1.24/bin/samtools

mkdir -p "$REF_DIR"

for i in {1..22} X Y M; do
    "$SAMTOOLS" faidx /tmp/gdc_data/GRCh38.d1.vd1.fa "chr$i" > "$REF_DIR/chr$i.fa"
    "$SAMTOOLS" faidx "$REF_DIR/chr$i.fa"
done

rm -rf /tmp/gdc_data /tmp/gdc_data.tar.gz
```

Получаю 25 файлов `chr[1-22,M,X,Y].fa` и 25 индексов `.fai`.

## 5. Запуск

При локальном запуске скрипт читает референсы из:

```text
/ref/GRCh38.d1.vd1_mainChr/sepChrs/
```

При запуске в Docker пробрасываю каталог с хостовой машины:

```bash
-v /mnt/data/ref/GRCh38.d1.vd1_mainChr/sepChrs/:/ref/GRCh38.d1.vd1_mainChr/sepChrs/:ro
```

Запускаю обработку:

```bash
python main.py \
    --input FP_SNPs_10k_GB38_twoAllelsFormat.tsv \
    --output result_FP_SNPs_10k_GB38_REF_ALT.tsv
```

Справка по аргументам:

```bash
python main.py --help
```

Скрипт проверяет заголовок и формат строк, работает с разными окончаниями строк, показывает индикатор выполнения и записывает сообщения с временными метками в лог.

## 6. Результат

Для 10 000 SNP получен результат:

```text
Распознано: 9991 (99.91%)
Нераспознано: 9 (0.09%)
```

Файлы после запуска:

```text
result_FP_SNPs_10k_GB38_REF_ALT.tsv
logs/<дата-время>/app.log
logs/<дата-время>/report.txt
logs/<дата-время>/unrecognized_SNPs.tsv
```

`result_FP_SNPs_10k_GB38_REF_ALT.tsv` содержит SNP, для которых удалось определить `REF` и `ALT`.

В `unrecognized_SNPs.tsv` попали 9 SNP. Для каждого из них `REFERENCE_BASE` из GRCh38.d1.vd1 не совпадает ни с `allele1`, ни с `allele2`, поэтому определить `REF` и `ALT` без догадки нельзя. Такие строки сохраняю отдельно вместе с референсным нуклеотидом и причиной. Причину самого расхождения по этим 9 позициям скрипт не определяет: его задача - проверить аллели по референсу и не подставлять `REF` при отсутствии совпадения.
