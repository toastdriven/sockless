import sockless


with sockless.open('irc.freenode.net:6665', mode='rw') as sock:
    # Writing.
    sock.write('NICK atestbot\r\n')
    sock.write('USER atestbot bot@aserver.com unused :atestbot\r\n')
    sock.write('JOIN #testbot\r\n')

    # Reading lines from a socket.
    for line in sock:
        if not line:
            break

        if 'End of /NAMES list' in line:
            print "Successfully connected & joined. Quitting."
            break

        print line.strip()
