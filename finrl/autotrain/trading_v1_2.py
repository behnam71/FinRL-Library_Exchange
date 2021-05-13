import pandas as pd
import datetime

#############################################################################
import warnings
warnings.filterwarnings('ignore')

#############################################################################
from finrl.config import config
from finrl.model.models import DRLAgent
from finrl.trade.backtest import backtest_plot, backtest_stats

from finrl.env.trade_env.env_stocktrading_stoploss_online import StockTradingEnvStopLossOnline

#############################################################################
# Append path for main project folder
import sys
sys.path.append("..\\FinRL-Library_Master")


#############################################################################
#############################################################################                 
def main():
    """
    agent trading
    """
    
    print("==============Start Trading===========")
    DDPG_model = "./" + config.TRAINED_MODEL_DIR + "/DDPG.model"

    #print("****Environment Document****")
    #print(StockTradingEnvStopLoss_online.__doc__)

    print("****Build Trade Environment****")
    file = open("./" + config.DATA_SAVE_DIR + "/balance.txt","r+") 
    initial_amount = file.read()
    initial_amount = float(initial_amount)
    file.close()
        
    information_cols = ["close", "macd", "boll_ub", "boll_lb", "rsi_30", "cci_30", "dx_30", \
                        "close_30_sma", "close_60_sma", "log_volume", "change", "daily_variance"]
    
    from pathlib import Path
    path = Path(__file__).resolve().parents[4].joinpath("AppData/Roaming/MetaQuotes/Terminal/2E8DC23981084565FA3E19C061F586B2/" \
                                                        "MQL4/Files/Leverage.txt")
    with open(path, 'r') as reader:
        Leverage = reader.read()
    print("Leverage : {}".format(Leverage))
    env_trade_kwargs = {'initial_amount': initial_amount*float(Leverage),
                        'sell_cost_pct': 0,
                        'buy_cost_pct': 0,
                        'hmax': 0.1,
                        'cash_penalty_proportion': 0.2,
                        'daily_information_cols': information_cols, 
                        'print_verbosity': 1, 
                        'discrete_actions': False}
    e_trade_gym = StockTradingEnvStopLossOnline(**env_trade_kwargs)
    
    print("****Model Prediction****")
    df_account_value, df_actions = DRLAgent.DRL_prediction_online(model=DDPG_model, 
                                                                  environment=e_trade_gym,
                                                                  n_days=2)
    
    print("****Prediction Resault Saving****")
    now = datetime.datetime.now().strftime("%Y-%m-%d-%HH%MM")
    df_account_value.to_csv("./" + config.RESULTS_DIR + "/_df_account_value_" + now + ".csv")
    df_actions.to_csv("./" + config.RESULTS_DIR + "/_df_actions_" + now + ".csv")
    
    print("****Get Backtest Results****")
    perf_stats_all = backtest_stats(account_value=df_account_value, value_col_name = 'total_assets')
    perf_stats_all = pd.DataFrame(perf_stats_all)
    perf_stats_all.to_csv("./" + config.RESULTS_DIR + "/_perf_stats_all_" + now + ".csv")
    

if __name__ == "__main__":
    main()
