import os
import sys, getopt
import datetime
import json
import urllib.request
import csv

# https://explorer.fuse.io/api-docs#block
# https://explorer.fuse.io/eth-rpc-api-docs
# https://www.coingecko.com/en/api/documentation

BLOCK_URL = "https://explorer.fuse.io/api?module=block&action=getblocknobytime&timestamp=TIMESTAMP&closest=before"
#BALANCE_URL = "https://explorer.fuse.io/api/eth-rpc/"
BALANCE_URL = "https://explorer-node.fuse.io/"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/fuse-network-token/market_chart/range?vs_currency=eur&from=DATE_FROM&to=DATE_TO"

def get_args(argv):
    coin = ''
    currency = ''
    year = 0
    day = 0
    help_string = 'Usage: python3 fuse_balances.py -a address -s start(yyyy-mm-dd) -e end(yyyy-mm-dd)'
    if len(argv) == 0:
        print(help_string)
        sys.exit(2)
    try:
        opts, args = getopt.getopt(argv,"ha:s:e:",["address=","start=","end="])
    except getopt.GetoptError:
        print(help_string)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(help_string)
            sys.exit()
        elif opt in ("-a", "--address"):
            address = arg
        elif opt in ("-s", "--start"):
            start_date = arg
        elif opt in ("-e", "--end"):
            end_date = arg
    return address, start_date, end_date

def get_block_number(timestamp):
    block_url = BLOCK_URL.replace("TIMESTAMP", str(timestamp))
    response = urllib.request.urlopen(block_url)
    data = response.read()
    values = json.loads(data)
    block_number = values['result']['blockNumber']

    #print(f"Block number: {block_number}")

    return block_number

def get_balance(address, block_number):
    raw_data = {
        "id":0,
        "jsonrpc":"2.0",
        "method": "eth_getBalance",
        "params": [address, hex(int(block_number))]
    }

    data = json.dumps(raw_data)

    # Convert to String
    data = str(data)

    # Convert string to byte
    data = data.encode('utf-8')

    req = urllib.request.Request(BALANCE_URL, data=data, headers={'Content-Type': 'application/json'}) # this will make the method "POST"
    #print(req)
    response = urllib.request.urlopen(req)
    #print(response)
    data = response.read()
    #print(data)
    values = json.loads(data)
    #print(values)

    return int(values['result'], 16) / 1e18

def get_balance3(address, block_number):
    #curl_command = f"""curl -X POST --insecure -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["{address}","{block_number}"],"id":0}' https://explorer.fuse.io/api/eth-rpc"""
    curl_command = "curl -X POST --insecure -H \"Content-Type: application/json\" --data '{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"ADDRESS\",\"BLOCK_NUMBER\"],\"id\":0}' https://explorer.fuse.io/api/eth-rpc 2> /dev/null"
    curl_command = curl_command.replace("ADDRESS", address).replace("BLOCK_NUMBER", block_number)
    #print(curl_command)
    import os
    stream = os.popen(curl_command)
    output = stream.read()
    #print(output)
    json_result = json.loads(output)
    #print(json.loads(output))
    if not 'result' in json_result:
        result = 0.0
    else:
        result = int(json_result['result'], 16) / 1e18

    #print(f"Balance: {result}")

    return result

def get_price(timestamp):
    url = COINGECKO_URL.replace("DATE_FROM", str(timestamp)).replace("DATE_TO", str(timestamp+3600))
    #print(url)
    response = urllib.request.urlopen(url)
    data = response.read()
    values = json.loads(data)
    #print(values)
    result = values['prices'][0][1]

    #print(f"Price: {result}")

    return result

def get_prices(start_timestamp, end_timestamp):
    url = COINGECKO_URL.replace("DATE_FROM", str(start_timestamp-3600)).replace("DATE_TO", str(end_timestamp+3600))
    #print(url)
    response = urllib.request.urlopen(url)
    data = response.read()
    values = json.loads(data)
    #print(values)
    result = values['prices']

    #print(f"Prices: {result}")
    #print(f"Prices: {result[:3]}")

    return result

def get_price_from_array(prices, current_timestamp):
    index = 0
    while int(prices[index][0] / 1000) < current_timestamp:
        index = index + 1

    timestamp = int(prices[index][0] / 1000)
    price = prices[index][1]

    #print(index, timestamp, price)
    return index, timestamp, price

def format_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def process_csv(csvwriter, array):
    for line in array:
        csvwriter.writerow([format_timestamp(line[0]), line[1], format_timestamp(line[2]), line[3]])


def  main(address, start_date, end_date):
    start_timestamp = int(datetime.datetime.strptime(start_date+"+00:00", "%Y-%m-%d%z").timestamp())
    end_timestamp = int(datetime.datetime.strptime(end_date+"+00:00", "%Y-%m-%d%z").timestamp())
    #print(f"start timestamp: {start_timestamp}")
    #print(f"end timestamp:  {end_timestamp}")
    prices = get_prices(start_timestamp, end_timestamp)
    index = 0
    data = []
    current_timestamp = start_timestamp
    while current_timestamp <= end_timestamp:
        block_number = get_block_number(current_timestamp)
        fuse_balance = get_balance(address, block_number)
        #price = get_price(current_timestamp)
        new_index, price_timestamp, price = get_price_from_array(prices[index:], current_timestamp)
        index = index + new_index

        data.append([current_timestamp, fuse_balance, price_timestamp, price])

        current_timestamp = current_timestamp + 86400 # 1 day

    if not os.path.exists("output"):
        os.mkdir("output")
    output_file = f'output/fuse_{address[:8]}_{start_date}_{end_date}.csv'
    #print(output_file)
    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',',
                            quotechar="'", quoting=csv.QUOTE_MINIMAL)
        process_csv(csvwriter, data)

    return

if __name__ == "__main__":
    address, start_date, end_date = get_args(sys.argv[1:])
    main(address, start_date, end_date)
