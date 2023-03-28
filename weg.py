class Bla:

    def __init__(self):
        pass

    def bla(func):
        print(func.__name__)
        def wrapper(self):
            print("Something is happening before the function is called.")
            func(self)
            print("Something is happening after the function is called.")
        return wrapper

    @bla
    def func_1(self):
        print("a")
        return False

    def main(self):
        a = self.func_1()
        print("und?")


bla = Bla()
bla.main()

