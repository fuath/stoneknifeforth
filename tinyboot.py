#!/usr/bin/python
"""Tiny bootstrapping interpreter for the first bootstrap stage.

Implements an extremely minimal Forth-like language, used to write
tinyboot1.tbf1.

The theory is that first we 'compile' the program by reading through
it to find compile-time definitions and actions, which sets up the
initial state of memory; then we 'run' the program by directly
interpreting its text, given that initial state.

"""
import sys, cgitb
cgitb.enable(format='text')

def debug(text):
    sys.stderr.write(text + "\n")

start_address = None
memory = []                  # a list of bytes represented as integers
stack = []
rstack = []

### Compile-time actions.
# Note that these should leave program_counter pointing after the
# last byte they consume.

program_counter = 0

def eat_byte():
    global program_counter
    program_counter += 1
def eat_comment():
    while program[program_counter] != ')': eat_byte()
    eat_byte()
def advance_past_whitespace():
    while program[program_counter] in ' \n': eat_byte()
def push_dataspace_label(n):
    return lambda: stack.append(n)
def dataspace_label():
    "Define a label in data space."
    advance_past_whitespace()
    name = program[program_counter]
    eat_byte()
    run_time_dispatch[name] = push_dataspace_label(len(memory))
def call_function(n):
    def rv():
        global program_counter
        rstack.append(program_counter)
        program_counter = n
    return rv
def define_function():
    advance_past_whitespace()
    name = program[program_counter]
    eat_byte()
    run_time_dispatch[name] = call_function(program_counter)
def read_number():
    start = program_counter
    while program[program_counter] in '0123456789': eat_byte()
    return int(program[start:program_counter])
def literal_byte():
    advance_past_whitespace()
    memory.append(read_number())
def as_bytes(num):
    "Convert a 32-byte number into a little-endian byte sequence."
    return [num & 255, num >> 8 & 255, num >> 16 & 255, num >> 24 & 255]
def literal_word():
    "Compile a little-endian literal 32-byte number into data space."
    advance_past_whitespace()
    memory.extend(as_bytes(read_number()))
def set_start_address():
    global start_address
    start_address = program_counter
def nop(): pass

compile_time_dispatch = {
    '(': eat_comment,
    'v': dataspace_label,
    ':': define_function,
    'b': literal_byte,
    '#': literal_word,
    '^': set_start_address,
    ' ': nop, '\n': nop,
}

def tbfcompile():
    while program_counter < len(program):
        byte = program[program_counter]
        eat_byte()
        if byte in compile_time_dispatch:
            compile_time_dispatch[byte]()
        elif byte in run_time_dispatch:
            pass                 # ignore things from run-time for now
        else:
            excerpt_beginning = max(0, program_counter - 10)
            assert False, '%r not defined at %r' % \
                   (byte, program[excerpt_beginning:program_counter])

### Run-time actions.
# Execution should pretty much stay inside of functions, and we
# shouldn't run into any compile-time actions there, right?
# Except maybe comments.

def write_out():
    "Given an address and a count, write out some memory to stdout."
    count = stack.pop()
    address = stack.pop()
    debug('writing address %d, count %d' % (address, count))
    sys.stdout.write(''.join([chr(memory[ii])
                              for ii in range(address, address+count)]))
def quit():
    sys.exit(0)
def add():
    stack.append(stack.pop() + stack.pop())
def push_literal():
    global program_counter
    program_counter -= 1
    stack.append(read_number())
def decode(bytes):
    return bytes[0] | bytes[1] << 8 | bytes[2] << 16 | bytes[3] << 24
def fetch():
    addr = stack.pop()
    stack.append(decode(memory[addr:addr+4]))
def store():
    addr = stack.pop()
    memory[addr:addr+4] = as_bytes(stack.pop())
def bitwise_not():
    stack.append(stack.pop() ^ 0xffffffff)
def return_from_function():
    global program_counter
    program_counter = rstack.pop()
def read_byte():
    stack.append(ord(sys.stdin.read(1)))

run_time_dispatch = {    
    '(': eat_comment,
    'W': write_out,
    'G': read_byte,
    'Q': quit,
    '+': add,
    '~': bitwise_not,
    '@': fetch,
    '!': store,
    ';': return_from_function,
    ' ': nop, '\n': nop,
}
for digit in '0123456789': run_time_dispatch[digit] = push_literal

def tbfrun():
    assert start_address is not None
    global program_counter
    program_counter = start_address
    while True:
        byte = program[program_counter]
        eat_byte()
        run_time_dispatch[byte]()

def main(infile):
    global program
    program = infile.read()
    tbfcompile()
    debug(str(memory))
    tbfrun()
    assert False, "tbfrun returned"

if __name__ == '__main__': main(file(sys.argv[1]))
