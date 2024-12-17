import shioaji as sj

print(sj.__version__)

api = 0
person_id = "A125841482"  # 身分證字號
api_key = "7ctn2iRqnbcC5k7X2tkxHZEcBUVNbsLHhmWYSPqA3Nbr"
secret_key = "8o7DB5fm8fBuK97JdXoXMQoWQTKoykLTgFdfsoCTYN7j"

CA_passwd = "A125841482"

api = sj.Shioaji(simulation=True)

api.login(api_key=api_key, secret_key=secret_key)

# 商品檔 - 請修改此處
contract = api.Contracts.Stocks.TSE["2890"]

# 證券委託單 - 請修改此處
order = api.Order(
    price=22,  # 價格
    quantity=1,  # 數量
    action=sj.constant.Action.Buy,  # 買賣別
    price_type=sj.constant.StockPriceType.LMT,  # 委託價格類別
    order_type=sj.constant.OrderType.ROD,  # 委託條件
    account=api.stock_account,  # 下單帳號
)

# 下單
trade = api.place_order(contract, order)
trade


# CA='c:\ekey\\551\\'+person_id+'\\S\\Sinopac.pfx'
# CA = '/home/roach/ekey/551/A125841482/S/Sinopac.pfx'
# result = api.activate_ca(
#     ca_path=CA,
#     ca_passwd=CA_passwd,
#     person_id=person_id,
# )

api = sj.Shioaji(simulation=False)

accounts = api.login(api_key=api_key, secret_key=secret_key)

print(accounts)
