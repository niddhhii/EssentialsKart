from flask import Flask, request, make_response, jsonify
import pyrebase
from datetime import date
import config
from firebase import firebase
import csv

app = Flask(__name__)

config = {
    "apiKey": config.apikey,
    "authDomain": config.authDomain,
    "databaseURL": config.databaseURL,
    "storageBucket": config.storageBucket,
    "serviceAccount": config.firebasesdk
}

firebaseObj = pyrebase.initialize_app(config)
fb_app = firebase.FirebaseApplication(config['databaseURL'], None)


@app.route('/')
def index():
    return 'Hello World!'


def getAction():
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    return action


def pushToDB():
    db = firebaseObj.database()
    req = request.get_json(force=True)
    params = req.get('queryResult').get('parameters')
    sess = req.get('session')[-36:] + "-" + str(date.today())
    curr_orders = fb_app.get('/orders', sess)
    if curr_orders is not None:
        item_list = params['items']
        num_list = params['number']
        order_dict = mkdict(curr_orders)
        k = len(order_dict)
        poslist = []
        neglist = []
        for i in range(len(item_list)):
            price = get_price(item_list[i])
            if price != -1:
                temp = [item_list[i], int(num_list[i]), price]
                order_dict.update({i + k: temp})
                poslist.append(item_list[i])
            else:
                neglist.append(item_list[i])
        db.child('orders').child(sess).update(order_dict)
    else:
        item_list = params['items']
        num_list = params['number']
        order_dict = {}
        poslist = []
        neglist = []
        for i in range(len(item_list)):
            price = get_price(item_list[i])
            if price != -1:
                temp = [item_list[i], int(num_list[i]), price]
                order_dict.update({i: temp})
                poslist.append(item_list[i])
            else:
                neglist.append(item_list[i])
        db.child('orders').child(sess).set(order_dict)
    text = ""
    if len(neglist) != 0:
        i = 0
        text = "We don't sell "
        for item in neglist:
            if i == (len(neglist) - 2):
                text += item + " and "
            elif i == (len(neglist) - 1):
                text += item + ". "
            else:
                text += item + ", "
            i += 1
        if len(poslist) != 0:
            text += "However, we have added "
            i = 0
            for item in poslist:
                if i == (len(poslist) - 2):
                    text += item + " and "
                elif i == (len(poslist) - 1):
                    text += item
                else:
                    text += item + ", "
                i += 1
            text += " to your cart."
    return text


def mkdict(temp):
    order_dict = {}
    i = 0
    for x in temp:
        order_dict.update({i: x})
        i += 1
    return order_dict


def get_price(item):
    with open('items.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                continue
            else:
                if row[0] == item:
                    return int(row[1])
        return -1


@app.route('/webhook', methods=['POST'])
def webhook():
    action = getAction()
    # print(action)
    if action == 'order_items':  # save items to session
        text = pushToDB()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'input.welcome':  # send the items pdf
        reply = {
            "fulfillmentText": "Send PDF",
        }
        return make_response(jsonify(reply))
    elif action == 'OrderItems.OrderItems-cancel':  # delete the session and end it
        reply = {
            "fulfillmentText": "Order Cancelled",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_details':  # ask for confirmation about order
        reply = {
            "fulfillmentText": "Details Confirmed",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_order':  # send final receipt over email and wapp
        reply = {
            "fulfillmentText": "Order confirmed",
        }
        return make_response(jsonify(reply))


if __name__ == '__main__':
    app.run()
