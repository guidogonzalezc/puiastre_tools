def palindromo(name):
    if len(name) <= 1:
        return True
    if name[0] != name[-1]:
        return False
    else:
        return palindromo(name[1:-1])

def palindromo_dos(name):
    return name == name[::-1]

print(palindromo("ana"))
print(palindromo_dos("anaa"))