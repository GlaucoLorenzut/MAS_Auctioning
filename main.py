import numpy as np
import seller
import buyer
import random
import statistics as stats
import janitor
import config as cfg
import plotting

if cfg.SEED:
    random.seed(cfg.SEED)


def launch_new_test(id, n_buyers, n_sellers, n_rounds, max_starting_price, max_bidding_factor, range_bidding_factor_increase, range_bidding_factor_decrease, epsilon, type, params={}):
    if n_sellers >= n_buyers:
        print("ERROR: (", id,") Buyers have to be more than Sellers")
        return None

    biddin_strategy_data, seller_strategy_data = None, None
    if params:
        biddin_strategy_data = params.get('BIDDING_STRATEGY')
        seller_strategy_data = params.get('SELLER_STRATEGY')


    # init OUTCOME
    outcome = []

    market_price_list, seller_profit_list, buyer_profit_list = [], [], []

    # init AGENTS
    seller_list = [seller.Seller(i) for i in range(n_sellers)]
    buyer_list = [buyer.Buyer(i, seller_list, max_bidding_factor, range_bidding_factor_increase, range_bidding_factor_decrease) for i in range(n_buyers)]

    for round in range(n_rounds):
        # for every round init this dict and added the lists of data during the auctions
        round_stats = {
            "id": round,
            "market_price": [],
            "seller_profit": [],
            "buyer_profit": []
        }

        # created a shuffled copy of the buyer_list and seller_list every round
        sellers = random.sample(seller_list, len(seller_list))
        buyers = random.sample(buyer_list, len(buyer_list))

        # start the auctions
        buyers_won_auction = {}  # only for leveled
        for slr in sellers:
            seller_price = slr.init_random_starting_price(max_starting_price)

            # the buyers start the bids
            bid_list = []
            for bur in buyers:
                # make the bid thanks to the factor given by the factor list
                buyer_bid = bur.get_bidding_factor(slr.id) * seller_price
                bid_list.append(buyer_bid)  # note: this bids have the same order of buyer_turn_list

            # bid end
            market_price = sum(bid_list) / len(bid_list)  # avg of all the bids

            round_stats["market_price"].append(market_price)

            bid_list = [(bid if bid <= market_price else 0) for bid in bid_list]  # remove the values over the market_price
            winner_index = bid_list.index(max(bid_list))  # found the first winner, the other ones... NO
            first_bid = bid_list[winner_index]
            bid_list[winner_index] = 0  # removed is offer (first_bid)...
            winner_payment = np.amax(bid_list)  # ...to pick the second max

            if not winner_payment:  # there is only one winner and the max is 0
                winner_payment = 0.5 * (first_bid + market_price)

            if type == "PURE_AUCTIONING":
                # profit for sellers
                seller_profit = winner_payment - seller_price

                # profit for buyers
                winner = buyers.pop(winner_index)  # remove the winner from the other auctions
                winner_profit = market_price - winner_payment
                for real_slr in seller_list:  # update the seller profit, Note: the real list
                    if real_slr.id == slr.id:
                        real_slr.add_to_profit(seller_profit)

                for real_bur in buyer_list:  # update the buyer profit, Note: the real list
                    if real_bur.id == winner.id:
                        real_bur.add_to_profit(winner_profit)

            elif type == "LEVELED_COMMITMENT_AUCTIONING":
                # profit for sellers
                seller_profit = winner_payment - seller_price

                # profit for buyers
                winner = buyers.__getitem__(winner_index)  # remove the winner from the other auctions
                winner_profit = market_price - winner_payment
                # add the buyer id inside the dict, if the key already exists, it return the previous value
                prev_auction = buyers_won_auction.setdefault(winner.id, (slr.id, winner_payment, winner_profit))
                penalty_fee = 0
                if prev_auction[0] != slr.id:
                    if winner_profit > prev_auction[2]:
                        penalty_fee = epsilon * prev_auction[1]
                        buyers_won_auction[winner.id] = (slr.id, winner_payment, winner_profit)
                    else:
                        penalty_fee = epsilon * winner_payment

                for real_slr in seller_list:  # update the seller profit, Note: the real list
                    if real_slr.id == slr.id:
                        real_slr.add_to_profit(seller_profit)
                    if real_slr.id == prev_auction[0]:
                        real_slr.add_to_profit(penalty_fee)

                for real_bur in buyer_list:  # update the buyer profit, Note: the real list
                    if real_bur.id == winner.id:
                        real_bur.add_to_profit(winner_profit)
                    if real_bur.id == prev_auction[0]:
                        real_bur.add_to_profit(-penalty_fee)

            if biddin_strategy_data:
                for b in bid_list:
                    if b == 0:
                        buyer_list[bid_list.index(b)].decrease_bid_factor(slr.id)
                    else:
                        buyer_list[bid_list.index(b)].increase_bid_factor(slr.id)
            elif seller_strategy_data:
                pass

        #round_stats["seller_profit"].append(seller_profit)
        #round_stats["buyer_profit"].append(winner_profit)
        round_stats["seller_profit"] = [seller.profit for seller in seller_list]
        round_stats["buyer_profit"] = [buyer.profit for buyer in buyer_list]
        outcome.append(round_stats)

    return outcome


def main():
    id_list, market_list, seller_list, buyer_list = [], [], [], []

    for test in cfg.test_list:

        if not test["execute"]:  # add this because we could want save tests on config but not test them sometimes
            continue

        result_list = []
        for n in range(test["times"]):
            result = launch_new_test(
                test["id"],
                test["n_buyers"],
                test["n_sellers"],
                test["n_rounds"],
                test["max_starting_price"],
                test["max_bidding_factor"],
                test["range_bidding_factor_increase"],
                test["range_bidding_factor_decrease"],
                test["epsilon"],
                test["type"],
                test["params"]
            )
            if not result:

                return 1
            else:
                result_list.append(result)

        round_list = range(test["n_rounds"])
        market_final_value, seller_final_value, buyer_final_value = [0] * test["n_rounds"], [0] * test["n_rounds"], [0] * test["n_rounds"]
        for result in result_list:
            avg_market_price_list, avg_seller_profit_list, avg_buyer_profit_list = [], [], []
            for round in result:
                avg_market_price = stats.mean(round["market_price"])
                avg_seller_profit = stats.mean(round["seller_profit"])
                avg_buyer_profit = stats.mean(round["buyer_profit"])

                avg_market_price_list.append(avg_market_price)
                avg_seller_profit_list.append(avg_seller_profit)
                avg_buyer_profit_list.append(avg_buyer_profit)

            market_final_value = [a + b for a, b in zip(market_final_value, avg_market_price_list)]
            seller_final_value = [a + b for a, b in zip(seller_final_value, avg_seller_profit_list)]
            buyer_final_value  = [a + b for a, b in zip(buyer_final_value, avg_buyer_profit_list)]

        market_final_value = np.array(market_final_value) / test["times"]
        seller_final_value = np.array(seller_final_value) / test["times"]
        buyer_final_value  =  np.array(buyer_final_value) / test["times"]


        plotting.plot_graph_result(test["id"], "market_price", round_list, market_final_value, cfg.STEP_PLOTTING, cfg.SHOW_SINGLE_GRAPH)
        plotting.plot_graph_result(test["id"], "seller_profit", round_list, seller_final_value, cfg.STEP_PLOTTING, cfg.SHOW_SINGLE_GRAPH)
        plotting.plot_graph_result(test["id"], "buyer_profit", round_list, buyer_final_value, cfg.STEP_PLOTTING, cfg.SHOW_SINGLE_GRAPH)

        plotting.plot_value_comparison("value_comparison", round_list, market_final_value, seller_final_value, buyer_final_value, cfg.STEP_PLOTTING, cfg.SHOW_SINGLE_GRAPH)

        id_list.append(test["id"]),
        market_list.append(market_final_value)
        seller_list.append(seller_final_value)
        buyer_list.append(buyer_final_value)


    plotting.plot_diff_results("test_comparison", round_list, id_list, market_list, seller_list, buyer_list, cfg.STEP_PLOTTING, cfg.SHOW_MULTI_GRAPH)

if __name__ == "__main__":
    janitor.create_dir("imgs")
    main()
