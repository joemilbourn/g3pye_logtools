import clint

print clint.args.grouped
print clint.args.grouped['-f']
print dir(clint.args.grouped['-f'])
print str(clint.args.grouped['-f'])
print clint.args.grouped['-f'].last
