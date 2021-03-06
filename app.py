import re
import json
import base64
import requests


class PhoneNumber:
	def __init__(self, num: str):
		self.num = num
		self.checkIfValid()

	def checkIfValid(self):
		# Open to better/more efficient checking ways - Fill a PR

		n = self.num
		assert n[0] == "+", "It seems that the phone indicatif was not provided!"
		assert len(n) in [12,13,14], "It seems that the provided phone number is not valid!"

		if n[1:3] in [32, 33, 34]:
			assert n[4] in [6,7] or n[5] in [6,7], "Looks like your phone number is not a mobile one!"

		assert not any([not char.isdigit() for char in n[1:]]), "Wait, there's letter in your phone number?"




class Zelf:
	API_HOST = "https://i.zelf.co"

	def __init__(self):
		self.s = requests.Session()
		self.s.headers = {
			"accept": "application/json",
			"accept-charset": "UTF-8",
			"content-type": "application/json",
			"host": "i.zelf.co",
			"user-agent": "Ktor client" # Unable to change..
		}

	def login(self, phone_number: PhoneNumber, otp_code: int=None) -> bool:
		PhoneNumber(phone_number)

		if otp_code is None: #aka login request
			r = self.s.post(
				self.API_HOST+"/auth/api/v1/registration",
				json={"cell_phone": phone_number, "channel": "Mobile"}
			).json()

			if r.get('confirmation_method') is None:
				err = r.get('type') + " – " + r.get('client_message')
				err += " Retry in " + str(r.get('retry_in') or r.get('extra_fields').get('retry_in'))
				return err, print(err)
		
			elif r.get('confirmation_method') == "OtpSms": #No other confirmation methods, yet?
				self.s.headers['x-confirmation-token'] = r['confirmation_token']
				self.retry_in_minimum = r.get('retry_in')

				return self.login(phone_number, otp_code=input("Login code (Sent by sms to your number): "))


		else: #aka login confirmation
			headers = self.s.headers
			headers['x-confirmation-code'] = otp_code

			r = self.s.put(
				self.API_HOST+"/auth/api/v1/registration",
				json={"cell_phone": phone_number, "channel": "Mobile"},
				headers=headers
			).json()

			if not r.get("state") == "Complete":
				err = r.get("type") + " – " + r.get("client_message")
				return err, print(err)


			del self.s.headers['x-confirmation-token']
			self.s.headers['cookie'] = "Authorization="+self.s.cookies['Authorization']

			r2 = self.s.post(
				self.API_HOST+"/auth/api/v1/identities/dh",
				json={
				  "client_open_key": "6L+Kp0oFXJ/P4Wb6TTrz7EEu/6YGjrTbE+fNJJst5hQ=", #what is that? r2 does return a server_open_key
				  "device": {
				    "device_token": {
				      "type_id": "Firebase",
				      "token": ""
				    },
				    "key": "e25bf559-f744-4546-a9a7-f02e5868e930", # phone uuid?
				    "name": "PULP 4G",
				    "version": "l5421",
				    "os": {
				      "type": "Android",
				      "name": "5.1.1",
				      "version": "22"
				    },
				    "vendor": "WIKO",
				    "imei": "",
				    "mac_addresses": [],
				    "rooted": false,
				    "options": []
				  },
				  "auth_type": "Device",
				  "group_id": "Curve25519" # what?
				}
			).json()

			r3 = self.s.get(self.API_HOST+f"/auth/api/v1/logon/scram/Device/{r2['login']}").json()
			r4 = self.s.post(
				self.API_HOST+"/auth/api/v1/logon/scram",
				json={
					"login": r2['login'],
					"server_nonce": r3['server_nonce'],
					"client_nonce": ..., # This random, but which random?
					"client_proof": ..., # This built over server salt/iteration (r3) and ???
					"auth_type": "Device",
					"channel": "Mobile"
				}
			)
			# r4, if successful, return a set-cookie header


			self.s.headers['cookie'] = "Authorization="+self.s.cookies['Authorization']

			r_test = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail")

			if r_test.status_code == 200:
				open("authtoken", "w").write(r_test['cookie'])
				return True, print("Successfully logged in")
			return False, print("Unable to login")

	def force_login(self, authorization_token: str) -> bool:
		if not authorization_token.startswith("Authorization="):
			authorization_token = "Authorization="+authorization_token
		self.s.headers['cookie'] = authorization_token


		r_test = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail")
		if r_test.status_code == 200:
			return True, print("Successfully logged in")

		del self.s.headers['cookie']
		return False, print("Unable to login using this auth token")


	def getAccountDetails(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail").json()

		self.account = {
			"id": r['customer_id'],
			"referral_id": r['referral_uid'],
			"state": r['state'],
			"type": r['customer_type'],
			"is_verified": False if r['identification_level'] == "NotIdentified" else True,
			"is_deleted": r['is_deleted'],
			"has_card": r['is_card_available'],
			"has_confirmed_phone": r['is_phone_confirmed'],
			"has_accepted_terms": r['accepted_terms'],
			"is_junior": r['has_junior_program'],
			"avatar": r['avatar_url'],
			"user": {
				"firstname": r['person']['person_name']['first_name'],
				"middlename": r['person']['person_name']['middle_name'],
				"lastname": r['person']['person_name']['last_name'],
				"gender": r['person']['gender'],
			},
			"achievements": r['achievements']
		}
		if self.account['is_junior'] is True:
			self.account['parent_id'] = r['parent_customer_id']
		
		if self.account['is_verified'] is True:
			self.account['user']['martial_status']: r['person']['martial_status'] #typo? might be marital | To watch
			self.account['user']['residence_country_code'] = r['person']['residence_country_code']
			self.account['user']['birth_infos'] = {
				"birth_date": r['person']['birth_date'],
				"birth_country": r['person']['birth_country'],
				"birth_place": r['person']['birth_place'],
			}

		return self.account

	def getCardsInfos(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/cards").json()

		self.cards = []
		for card in r:
			self.cards.append(
				{
					"id": card['id'],
					"is_active": True if card['status'] == "Active" else False,
					"currency": card['currency'],
					"owner": card['embossed_name'],
					"striked_card_number": card['masked_card_number'],
					"created_on": card['open_date'],
					"balance": card['balance']['value']
				}
			)

		return self.cards

	def getBonusDetails(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/bonusaccounts").json()

		self.bonuses = r

		return self.bonuses

	def getCardDetails(self, card_id: int) -> dict:
		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/requisites").json()

		for i in range(len(self.cards)):
			if self.cards[i]['id'] == card_id:
				break

		self.cards[i]['clear_number'] = base64.b64decode(r['number']).decode('utf-8')
		self.cards[i]['expiration_date'] = r['expiry_date']

		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/cvc").json()
		self.cards[i]['cvv'] = base64.b64decode(r['cvc']).decode('utf-8')

		return self.cards[i]

	def getIbanInfos(self):
		r = self.s.get(self.API_HOST+"/sme/api/v1/cards/topup/iban").json()

		self.iban = r
		return r

	def getLimitsInfos(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/limits").json()

		self.limits = {
			"spending": {
				"spent": r['spending']['period_30_days']['current_amount']['value'],
				"limit": r['spending']['period_30_days']['limit_amount']['value'],
			},
			"topup": {
				"topped_up": r['topup']['period_30_days']['current_amount']['value'],
				"limit": r['topup']['period_30_days']['limit_amount']['value']
			}
		}
		self.limits['spending']['left'] = self.limits['spending']['limit']-self.limits['spending']['spent']
		self.limits['topup']['left'] = self.limits['topup']['limit']-self.limits['topup']['topped_up']

		return self.limits


	def getCardTopupLink(self, card_id: int, short_link: bool=False) -> str:
		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/hipay-link").json()

		if short_link:
			return r.get('url')


		url_token = r.get('url').split('/')[-1]

		headers = self.s.headers
		headers['content-type'] = "application/x-www-form-urlencoded"

		r = self.s.post(
			self.API_HOST+"/auth/api/v1/logon/tiny-token",
			data={
				"Token": url_token,
				"Channel": "telegram",
				"FailureUrl": "/link-expired"
			},
			headers=headers
		)

		return r.url

	def getTopupFee(self, destination_card: int, amount_to_topup: int) -> float:
		r = self.s.post(
			self.API_HOST+"/sme/api/v1/transfers/card-to-card/fee",
			json={
				"amount": {"value": amount_to_topup, "currency": "EUR"},
				"destination_card": {"identity": "ID", "card_id": destination_card}}
		).json()

		if r.get('type'): #error
			return r['message']

		return r['amount']['value']


	def topupCard(self, card_id: int, amount: float, source_card: dict, user_info: dict) -> bool|None:
		# source_card = {"identity": "Number", number": "5100000000000034", "cvc": "000", "expiry_date": {"month": 1, "year": 2000}}
		# user_info = {"firstname": "XXX", "lastname": "XXX", "country": "FR",
		#				"city": "CITYNAME", "zipcode": "ZIPCODE",
		#				"streetaddress": "XX rue XXXXXXX, ZIPCODE CITYNAME, France"}
		#				"streetaddress2": None}
		
		data = {
			"external_id": "13 char integer", # TODO: Investigate to found its origin
			"browser_info": {
				"javascript_enabled": True, "java_enabled": False,
				"color_depth":24, "screen_height":768, "screen_width":1366,
				"timezone":"-60"
			},
			"amount": {"value": amount, "currency":"EUR"},
			"source_card": source_card,
			"destination_card": {"identity": "ID", "card_id": card_id},
			"user_info": user_info
		}
			
		headers = self.s.headers
		headers['user-agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
		r = self.s.post(
			self.API_HOST+"/sme/api/v1/transfers/card-to-card",
			json=data,
			headers=headers
		)

		if r.status_code == 400:
			return print(r.get('message'))



	#def hack(self):
	#	r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/668002/hipay-link").json()
	#	print(r)



z = Zelf()
with open("authtoken", "a+") as f:
	f.seek(0)
	auth_token = f.read()

login_result = z.force_login(auth_token)
if type(login_result) == tuple and login_result[0] is False:
	if z.login(phone_number=input("Your ZELF account phone number: ")) [0] is not True:
		print()
		raise Exception("Unable to login!")


print( z.getAccountDetails() )
print( z.getCardDetails(z.getCardsInfos()[0]['id']) )
#print( z.getCardTopupLink(z.cards[0]['id']) )
#print( z.getIbanInfos() )
#print( z.getTopupFee(z.cards[0]['id'], 125.75) )
#print( z.hack() )
