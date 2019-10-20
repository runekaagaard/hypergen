class ChangeAware(object):
    def __init__(self, data):
        self.in_init = True
        self.data = data
        self.path = [data]
        self.in_init = False

    def __setattr__(self, k, v):
        if k == "in_init" or self.in_init is True:
            object.__setattr__(self, k, v)
        else:
            setattr(self.path[-1], k, v)

    def __setitem__(self, k, v):
        print "Setting", k, v
        self.path[-1][k] = v

    def __getattr__(self, k):
        return self.path[-1][k]


class X(object):
    y = 1


data = ChangeAware(dict(x=X()))
data.x.y = 1234
print data.x.y

#data.foo = 42
#data[3] = 91
#setattr(data, 3, 91)

print data.foo.changed()
