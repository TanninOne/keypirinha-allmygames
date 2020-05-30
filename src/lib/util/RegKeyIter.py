from winreg import EnumKey

class RegKeyIter:
    """
    convenience tool to iterate through registry keys
    """
    def __init__(self, base_key):
        self.__base_key = base_key

    def __iter__(self):
        self.__idx = 0
        return self
  
    def __next__(self):
        try:
            next_name = EnumKey(self.__base_key, self.__idx)
            self.__idx += 1
            return next_name
        except Exception:
            raise StopIteration
