import math
width = 257
n = math.floor(math.log(width,2)) + 1

with open("args.txt", 'w') as file:
    for frac in [0, 0.0125]:
        for acc in [1, 5]:
            for t in [1000, 2000, 4000, 8000, 16000, 32000, 64000]:
                for workers in [1, 2, 4, 8, 15]:
                    args = f"-workers {workers} -sleep 1 -strong 0 -steps {n} -isync 0 -restrict 0 -t {t} -deps 1 -frac {frac} -accesses {acc} -width {width}\n"
                    file.write(args)

# with open("args.txt", 'w') as file:
#     for frac in [0]:
#         for acc in [1]:
#             for t in [1000]:
#                 for workers in [1]:
#                     args = f"-workers {workers} -sleep 1 -strong 0 -steps {n} -isync 0 -restrict 0 -t {t} -deps 1 -frac {frac} -accesses {acc} -width {width}\n"
#                     file.write(args)