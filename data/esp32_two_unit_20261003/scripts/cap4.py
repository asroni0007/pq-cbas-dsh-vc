import serial, sys, time
port, out = sys.argv[1], sys.argv[2]
s = serial.Serial(port, 57600, timeout=1)
s.dtr = False
s.rts = False
f = open(out, 'w')
started = False
lines = 0
restarts = 0
t0 = time.time()
tb = t0
print('Menunggu... (jangan sentuh papan)', flush=True)
while time.time() - t0 < 1700:
    l = s.readline().decode(errors='replace')
    if not l:
        continue
    if '[PLATFORM] ESP32' in l:
        if started and lines >= 60:
            f.write('RESET_DETECTED\n')
            ex = [l]
            for _ in range(6):
                ex.append(s.readline().decode(errors='replace'))
            for e in ex:
                f.write(e)
                print(e.rstrip(), flush=True)
            f.close()
            print('RESET DI TENGAH RUN setelah %d baris, %d detik - log tidak valid' % (lines, time.time() - tb))
            sys.exit(1)
        f.seek(0)
        f.truncate()
        lines = 0
        started = True
        restarts += 1
        tb = time.time()
        print('mulai (boot ke-%d)' % restarts, flush=True)
    if started:
        f.write(l)
        f.flush()
        lines += 1
        if lines % 200 == 0:
            print(lines, 'baris', flush=True)
        if 'ESP32_UECC_BASELINE_OK' in l or '_FAIL' in l:
            print('SELESAI', lines, 'baris', int(time.time() - tb), 'detik')
            break
f.close()
