import requests as req


API_BASEURL = "https://i.zelf.co"

def getUserTelegram(ref_code: str) -> str|None:
	r = req.get(f"{API_BASEURL}/sme/api/v1/opendata/customers/retail/{ref_code}").json()
	assert r.get("type") != "bad_request", "Invalid referral code"

	if not r['nickname']:
		return print("User did not linked its Telegram to ZELF")
	
	return f"https://t.me/{r['nickname']}"

def getUserFirstname(ref_code: str) -> str:
	r = req.get(f"{API_BASEURL}/sme/api/v1/opendata/customers/retail/{ref_code}").json()
	assert r.get("type") != "bad_request", "Invalid referral code"

	return r['masked_person_name'].split()[-2] #Not using index 0 as some users have an emote before name

def getUserCountry(ref_code: str) -> str:
	r = req.get(f"{API_BASEURL}/sme/api/v1/opendata/customers/retail/{ref_code}").json()
	assert r.get("type") != "bad_request", "Invalid referral code"

	return r['country_code']

def getUserStrikedPhoneNumber(ref_code: str) -> str:
	r = req.get(f"{API_BASEURL}/sme/api/v1/opendata/customers/retail/{ref_code}").json()
	assert r.get("type") != "bad_request", "Invalid referral code"

	return r['masked_onmt']


code = ""

print( getUserTelegram(code) )
print( getUserFirstname(code) )
print( getUserCountry(code) )
print( getUserStrikedPhoneNumber(code) )