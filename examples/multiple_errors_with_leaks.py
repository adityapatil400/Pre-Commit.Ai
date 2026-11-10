# Syntax errors and resource leak in same file
for j into range(1, 10):
    f = open('output.txt', 'w')
    f.write(str(j))

{

