import csv


class CsvRowReader:
    """Index a CSV file so rows can be fetched by integer offset."""

    def __init__(self, path):
        f = open(path, "r")
        self.file = f
        self.reader = csv.reader(f)
        self.offset_list = []
        while True:
            self.offset_list.append(f.tell())
            line = f.readline()
            if line == "":
                break
        self.offset_list.pop()
        self.num_rows = len(self.offset_list)

    def __del__(self):
        self.file.close()

    def read_row(self, idx):
        self.file.seek(self.offset_list[idx])
        return next(self.reader)


def read_corpus_batch(input_reader, start_idx, batch_size):
    corpus_rows = []
    for offset in range(batch_size):
        row_idx = start_idx + offset
        if row_idx < input_reader.num_rows:
            corpus_rows.append(input_reader.read_row(row_idx))
    return corpus_rows


def iter_corpus_batches(input_reader, start_id, batch_size, end_id=None):
    stop = input_reader.num_rows if end_id is None else min(end_id, input_reader.num_rows)
    for batch_start in range(start_id, stop, batch_size):
        this_batch = min(batch_size, stop - batch_start)
        corpus_rows = read_corpus_batch(input_reader, batch_start, this_batch)
        if corpus_rows:
            yield batch_start, corpus_rows
