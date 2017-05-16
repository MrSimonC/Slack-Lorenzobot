from custom_modules.sdplus_api_rest import API


class ApiNbt(API):
    """
    Extends basic sdplus api rest module, specifically for NBT
    """
    def __init__(self, key, base_url):
        self.__version__ = '0.2'
        API.__init__(self, key, base_url)

    @staticmethod
    def get_impact(digit):
        if digit == '1':
            return '1 Impacts Organisation'
        elif digit == '2':
            return '2 Impacts Site or Multiple Departments'
        elif digit == '3':
            return '3 Impacts Department'
        elif digit == '4':
            return '4 Impacts End User'
        elif digit == '5':  # testing group
            return '5 Impact not known'
        else:
            return ''

    @staticmethod
    def get_urgency(digit):
        if digit == '1':
            return '1 Business Operations Severely Affected - Requires immediate response'
        elif digit == '2':
            return '2 Business Operations Significantly Affected - Requires response within 4 hours of created time'
        elif digit == '3':
            return '3 Business Operations Slightly Affected - Requires response within 8 hours of created time'
        elif digit == '4':
            return '4 Business Operations Not Affected - Requires response within 16 hours of created time'
        elif digit == '5':  # testing group
            return '5 Not supported by IM&T'
        else:
            return ''


