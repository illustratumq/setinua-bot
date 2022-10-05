import datetime
import locale
import pprint

print(datetime.datetime.now().strftime('%a %d, %B'))
# pprint.pprint(locale.locale_alias)
locale.setlocale(locale.LC_ALL, 'uk_UA.UTF8')
print(datetime.datetime.now().strftime('%a %d, %B'))
