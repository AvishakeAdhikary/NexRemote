package com.neuralnexusstudios.nex_remote.core.network

import java.net.InetAddress
import java.net.Socket
import javax.net.SocketFactory

/**
 * Plain sockets with TCP_NODELAY on (Nagle off).
 *
 * Input traffic is many tiny messages with nothing flowing back from the PC. With Nagle on, each
 * message waits for the previous one's ACK, and Windows delays ACKs by up to 200 ms, so the
 * touchpad stutters while screen control (where the PC streams frames back) feels fine.
 * OkHttp wraps these sockets for TLS on the secure port, so this covers both ports.
 */
class NoDelaySocketFactory(private val delegate: SocketFactory = getDefault()) : SocketFactory() {
    private fun Socket.tuned(): Socket = apply {
        tcpNoDelay = true
        keepAlive = true
    }

    override fun createSocket(): Socket = delegate.createSocket().tuned()

    override fun createSocket(host: String?, port: Int): Socket = delegate.createSocket(host, port).tuned()

    override fun createSocket(host: String?, port: Int, localHost: InetAddress?, localPort: Int): Socket =
        delegate.createSocket(host, port, localHost, localPort).tuned()

    override fun createSocket(host: InetAddress?, port: Int): Socket = delegate.createSocket(host, port).tuned()

    override fun createSocket(address: InetAddress?, port: Int, localAddress: InetAddress?, localPort: Int): Socket =
        delegate.createSocket(address, port, localAddress, localPort).tuned()
}
