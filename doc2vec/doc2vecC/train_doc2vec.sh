DATA_PATH=train_data.txt

rm doc2vecc
gcc doc2vecc.c -o doc2vecc -lm -pthread -O3 -march=native -funroll-loops

time ./doc2vecc -train ./$DATA_PATH -word wordvectors.txt -output docvectors.txt -cbow 1 -size 256 -window 10 -negative 5 -hs 0 -sample 0 -threads 4 -binary 0 -iter 30 -min-count 10 -test ./$DATA_PATH -sentence-sample 0.1 -save-vocab alldata.vocab
