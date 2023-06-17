import sys
from csv import writer

args = sys.argv
input_path = args[1]
output_path = args[2]
exc_data = open(input_path, "r").readlines()
output_l = []
output_l_append = output_l.append
with open(output_path, "w") as f:
    writer_ = writer(f)
    for row in exc_data:
        row_splited = row.split(" ")
        writer_.writerow(
            [
                row_splited[0].replace("-", " ").replace("\n", ""),
                row_splited[-1].replace("-", " ").replace("\n", ""),
            ]
        )
