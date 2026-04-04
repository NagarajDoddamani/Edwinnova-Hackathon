import json

def convert_json_to_jsonl(input_path: str, output_path: str):
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        data = json.load(infile)
        for entry in data:
            json.dump(entry, outfile)
            outfile.write('\n')
    return output_path
