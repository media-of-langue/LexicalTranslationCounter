for n in range(5,11):
    print(f"cat en_it_corpus_00{str(n)}*.csv > ~/corpus_it_en_{str(n)}.csv" ,end="")
    if n!=10:
        print(" && ")
