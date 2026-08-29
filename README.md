# SNP-addition

Дополняет файл с SNP из GRAF 2.4 через GRCh38 геном человека

Формирование FP_SNPs_10k_GB38_twoAllelsFormat.tsv из FP_SNPs.txt

```bash
curl -L http://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/GetZip.cgi?zip_name=GRAF_files.zip \
  | tar -zxf -  -C /tmp/ \
  && awk -F'\t' 'BEGIN {OFS="\t"} \
      NR==1 { print "#CHROM", "POS", "ID", "allele1", "allele2"; next } \
      { if ($2 == "23") { next }; print $2="chr"$2, $4, "rs"$1, $5, $6 }' \
      /tmp/data/FP_SNPs.txt > FP_SNPs_10k_GB38_twoAllelsFormat.tsv \
  && rm -rf /tmp/data
```

Скачивание и установка samtools

```bash
# samtools install
curl -L https://github.com/samtools/samtools/releases/download/1.24/samtools-1.24.tar.bz2 \
  | tar -xj -C /tmp
```

Разделение GRCh38.d1.vd1.fa на 25 файлов через samtools

```bash
mkdir -p /ref/GRCh38.d1.vd1_mainChr/sepChrs/

for i in {1..22} X Y M; do
    /content/samtools-1.24/bin/samtools faidx /tmp/gdc_data/GRCh38.d1.vd1.fa chr$i > /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa
    /content/samtools-1.24/bin/samtools faidx /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa > /ref/GRCh38.d1.vd1_mainChr/sepChrs/chr$i.fa.fai
    echo "chr$i"
done
```
