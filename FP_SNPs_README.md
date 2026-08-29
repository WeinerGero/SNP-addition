## Клонирование репозитория

```bash
git clone https://github.com/WeinerGero/SNP-addition.git /content/SNP-addition
```

## Формирование FP_SNPs_10k_GB38_twoAllelsFormat.tsv из FP_SNPs.txt

```bash
# скачивание и распаковка  GRAF 2.4, обработка FP_SNPs.txt: переименовывание заголовков,
# пропуск половых хромосом, добавление префиксов и перестановка колонок
# копирование FP_SNPs.txt в репозиторий и очищение иходников
curl -L http://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/GetZip.cgi?zip_name=GRAF_files.zip \
  | tar -zxf -  -C /tmp/ \
  && awk -F'\t' 'BEGIN {OFS="\t"} \
      NR==1 { print "#CHROM", "POS", "ID", "allele1", "allele2"; next } \
      { if ($2 == "23") { next }; print $2="chr"$2, $4, "rs"$1, $5, $6 }' \
      /tmp/data/FP_SNPs.txt > /content/SNP-addition/FP_SNPs_10k_GB38_twoAllelsFormat.tsv \
  && cp /tmp/data/FP_SNPs.txt /content/SNP-addition/FP_SNPs.txt \
  && rm -rf /tmp/data
```

## Скачивание и установка samtools

```bash
# установка зависимостей
apt-get update -qq
apt-get install -y build-essential zlib1g-dev libncurses-dev

# скачивание и распаковка samtools 1.24
curl -L https://github.com/samtools/samtools/releases/download/1.24/samtools-1.24.tar.bz2 \
  | tar -xj -C /tmp

# сборка и установка samtools 1.24
cd /tmp/samtools-1.24 && \
  ./configure --prefix=/content/samtools-1.24 && \
  make -j"$(nproc)" && \
  make install
```

## Скачивание и распаковка референсного генома человека версии GRCh38.d1.vd1

```bash
curl -L -o gdc_data.tar.gz https://api.gdc.cancer.gov/data/254f697d-310d-4d7d-a27b-27fbf767a834 \
    && mkdir -p /tmp/gdc_data \
    && tar -xzf gdc_data.tar.gz -C /tmp/gdc_data
```

## Разделение GRCh38.d1.vd1.fa на 25 файлов через samtools

```bash
# создание папки с учётом родительских папок
mkdir -p /ref/GRCh38.d1.vd1_mainChr/sepChrs/

# формирование .fa и .fai для яхромосом 1-22, а также X, Y и M через samtools
for i in {1..22} X Y M; do
    /content/samtools-1.24/bin/samtools faidx /tmp/gdc_data/GRCh38.d1.vd1.fa chr$i > /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa
    /content/samtools-1.24/bin/samtools faidx /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa > /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa.fai
    echo "chr$i"
done

# удаление исходников
rm -rf /tmp/gdc_data
```
