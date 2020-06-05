import csv
import smtplib
from datetime import date
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

import pyrebase
from firebase import firebase
from flask import Flask, request, make_response, jsonify
from jinja2 import Environment, FileSystemLoader
from twilio.rest import Client

import config

app = Flask(__name__)

config = {
    "apiKey": config.apikey,
    "authDomain": config.authDomain,
    "databaseURL": config.databaseURL,
    "storageBucket": config.storageBucket,
    "serviceAccount": config.firebasesdk,
    "twilioSID": config.twilioSID,
    "twilioAUTH": config.twilioAUTH,
    "appPWD": config.appPWD,
    "fromEmail": config.fromEmail
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
    sess = req.get('session')[-13:] + "-" + str(date.today())
    curr_orders = fb_app.get('/orders', sess)
    if curr_orders is not None:
        item_list = params['items']
        num_list = params['number']
        order_dict = curr_orders
        poslist = []
        neglist = []
        for i in range(len(item_list)):
            price = get_price(item_list[i])
            if item_list[i] not in order_dict:
                if price != -1:
                    temp = {item_list[i]: [int(num_list[i]), price]}
                    order_dict.update(temp)
                    poslist.append(item_list[i])
                else:
                    neglist.append(item_list[i])
            else:
                prev = order_dict[item_list[i]][0]
                order_dict[item_list[i]][0] = prev + int(num_list[i])
                poslist.append(item_list[i])
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
                temp = {item_list[i]: [int(num_list[i]), price]}
                order_dict.update(temp)
                poslist.append(item_list[i])
            else:
                neglist.append(item_list[i])
        db.child('orders').child(sess).set(order_dict)
    text = ""
    if len(neglist) != 0:
        i = 0
        text = "Sorry, we don't sell "
        for item in neglist:
            if i == (len(neglist) - 2):
                text += item + " and "
            elif i == (len(neglist) - 1):
                text += item + ". "
            else:
                text += item + ", "
            i += 1
        text += "Please refer to the list we sent you earlier. "
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


def sendPDF(url):
    req = request.get_json(force=True)
    username = config['twilioSID']
    password = config['twilioAUTH']
    client = Client(username=username, password=password)
    from_whatsapp_number = 'whatsapp:+14155238886'
    to_whatsapp_number = req.get('session')[-13:]
    client.messages.create(body='EssentialsKart Products',
                           media_url=url,
                           from_=from_whatsapp_number,
                           to=to_whatsapp_number)
    ch_contact = fb_app.get('/users', to_whatsapp_number)
    if ch_contact is not None:
        name = ch_contact['name']
        client.messages.create(
            body='Hey ' + name + '! Glad to see you again. It\'s Natasha again from EssentialsKart. Here to help you '
                                 'out in your order. '
                                 'Please check the list below to find the essential items that you can order '
                                 'during lockdown. So, what would you like to order today?',
            from_=from_whatsapp_number,
            to=to_whatsapp_number)
    else:
        client.messages.create(
            body='Hey! I am Natasha from EssentialsKart. Here to help you out in your order. '
                 'Please check the list below to find the essential items that you can order '
                 'during lockdown. So, what would you like to order today?',
            from_=from_whatsapp_number,
            to=to_whatsapp_number)


def genPDF():
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("invoice.html")
    template_vars = {"title": "Sales Funnel Report - National",
                     "national_pivot_table": ''}
    html_out = template.render(template_vars)
    pdf = ""
    # HTML(string=html_out).write_pdf("report.pdf")

    return pdf


def del_sess():
    req = request.get_json(force=True)
    sess = req.get('session')[-36:] + "-" + str(date.today())
    fb_app.delete('/orders', sess)


def check_phone():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    ch_contact = fb_app.get('/users', phone)
    if ch_contact is not None:
        name = ch_contact['name']
        return name + ", please enter your passcode to proceed."
    else:
        return "We have to setup an account for you to proceed further. Please enter your name."


def conf_details():
    req = request.get_json(force=True)
    details = req.get('queryResult').get('parameters')
    contact = req.get('session')[-13:]
    db = firebaseObj.database()
    details_dict = {'name': details['name']['name'].title(), 'email': details['email'], 'zipcode': details['zipcode']}
    db.child('users').child(contact).set(details_dict)
    return ""


def get_order():
    req = request.get_json(force=True)
    sess = req.get('session')[-13:] + "-" + str(date.today())
    curr_orders = fb_app.get('/orders', sess)
    print(curr_orders)
    text = ""
    i = 1
    sums = 0
    for item in curr_orders:
        sums += curr_orders[item][0] * curr_orders[item][1]
        text += "{}. {}     {}  x    Rs. {}  =>  Rs. {}<br>".format(i, item.title(), curr_orders[item][0],
                                                                    curr_orders[item][1],
                                                                    (curr_orders[item][0] * curr_orders[item][1]))
        i += 1
    text += "Grand Total: {}<br>".format(sums)
    return text


def check_pwd():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    password = fb_app.get('/users', phone)['passcode']
    passcode = req.get('queryResult').get('parameters')['passcode']
    if password != passcode:
        return "Wrong passcode. Please try again."
    else:
        return "Authentication successful. Would you like to pay cash on delivery or by card?"


def add_pwd():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    passcode = req.get('queryResult').get('parameters')['new_passcode']
    ph = fb_app.get('/users', phone)
    if len(str(int(passcode))) == 4 and str(int(passcode)).isnumeric():
        ph.update({'passcode': passcode})
        db = firebaseObj.database()
        db.child('users').child(phone).update(ph)
        return "Congrats, " + ph['name'] + "! You are all set. Would you like to pay cash on delivery or by card?"
    else:
        return "Please enter a valid 4 digit numerical passcode."


def add_mode():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    mode = req.get('queryResult').get('parameters')['mop']
    ph = fb_app.get('/users', phone)
    ph['mode'] = mode
    db = firebaseObj.database()
    db.child('users').child(phone).update(ph)
    order = get_order()
    return "This is your order summary.<br>" + order + " Reply 'Yes' to confirm order and 'No' to cancel."


def conf_order():
    pdf = genPDF()  # here we'll receive a pdf
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    ph = fb_app.get('/users', phone)
    email = ph['email']
    name = ph['name']
    message = "Hey {},\n Thank you for ordering with us. We hope you find our services useful. Here is your invoice." \
        .format(name)
    text = sendmail(email, message, pdf)
    return text


def sendmail(to_email, message, pdf):
    from_email = config['fromEmail']
    password = config['appPWD']
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Order Confirmed - EssentialsKart"
    msg['From'] = from_email
    msg['To'] = to_email

    # msgText = MIMEText(message + '<img width="100%" src="cid:image">', 'html')
    msg.attach(message)

    fp = open(pdf, 'rb')  # pdf path or object
    msgImage = MIMEImage(fp.read())
    fp.close()
    msgImage.add_header('Content-ID', '<image>')
    msg.attach(msgImage)

    response = {}
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(from_email, password)
            print("Sending Mail:", to_email)
            s.sendmail(from_email, to_email, msg.as_string())
        response['email_status'] = "Success"
    except Exception as err:
        print(err)
        response['email_status'] = "Failed"
    return response


def edit_order():
    return ""


def edit_details():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    params = req.get('queryResult').get('parameters')
    data = fb_app.get('/users', phone)
    for key in params:
        if params[key] != "":
            if key == "name1":
                data[key.replace("1", "")] = params['name1']['name']
            else:
                data[key.replace("1", "")] = params[key]
    db = firebaseObj.database()
    db.child('users').child(phone).set(data)
    return "Are your details correct now?"


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    action = getAction()
    if action == 'order_items':  # save items to session
        text = pushToDB()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'input.welcome':  # send the items pdf
        url = "https://github.com/ItsTheKayBee/chatbot-webhook-API/raw/master/price_list.pdf"
        # sendPDF(url)      # uncomment later
        reply = {
            "fulfillmentText": "",
        }
        return make_response(jsonify(reply))
    elif action == 'OrderItems.OrderItems-cancel':  # delete the session and end it
        del_sess()
        reply = {
            "fulfillmentText": "",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_details':  # ask for confirmation about order
        text = conf_details()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_order':  # send final receipt over email and wapp
        text = conf_order()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'edit_order':  # edit order
        text = edit_order()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'edit_details':  # edit individual detail
        text = edit_details()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'stop_order':  # check phone
        text = check_phone()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'check_passcode':  # check phone
        text = check_pwd()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'get_passcode':  # check phone
        text = add_pwd()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'mode':  # check phone
        text = add_mode()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))


if __name__ == '__main__':
    app.run()
