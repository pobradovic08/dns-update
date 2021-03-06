# -*- coding: utf-8 -*-
# DNS PTR updater
# Copyright (C) 2017  Pavle Obradovic (pajaja)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import easysnmp
import re
import logging

from device_interface import DeviceInterface
from dns_check import DnsCheck


class Device:
    def __init__(self, hostname, config, dns=None):
        """
        Initialize instance with empty interfaces array
        :param hostname:    Hostname of device. Must be FQDN
        :param config:      Config instance
        """
        self.logger = logging.getLogger('dns_update.device:%s' % hostname)
        self.session = None
        self.config = config
        self.interfaces = {}
        self.hsrp_addresses = {}
        self.ignored = False
        self.dns = dns if dns else DnsCheck(self.config)
        self.hostname = hostname
        # Split device.hostname into two parts: (hostname).(domain.example)
        try:
            self.host, self.domain = self.hostname.split('.', 1)
        except ValueError:
            self.host = self.hostname
            self.domain = None
        # Get IN A record for device hostname
        self.ip = self.dns.get_a(self.hostname)
        # TODO: update to support v3
        self.community = config.get_snmp_community(self.hostname)
        self.ignored = self.config.is_device_ignored(self.hostname)

    def get_interfaces(self):
        """
        Walks trough the
        and fetches IP address and  IF-MIB::ifIndex
        :return:
        """

        # If device is on ignore list skip interface discovery
        # Interfaces dictionary will be empty
        if self.ignored:
            self.logger.info("Device ignored. SKipping...")
            return True

        # Setup SNMP session
        try:
            self.logger.debug("Establishing SNMP session to '%s'" % self.hostname)
            self.session = easysnmp.Session(
                hostname=self.hostname,
                community=self.community,
                use_numeric=True,
                version=2,
                timeout=self.config.get_snmp_timeout(),
                retries=self.config.get_snmp_retries(),
                abort_on_nonexistent=True
            )

            # Fetch HSRP VIP addresses
            hsrp_addresses = self._get_hsrp_addresses()

            """
            Implemented OID IP-MIB::ipAdEntIfIndex (1.3.6.1.2.1.4.20.1.2) is apparently deprecated.
            The new IP-MIB::ipAddressIfIndex is not implemented on most network devices.
            """

            # Compiled regexp pattern - ipAdEntIfIndex + important dot ;)
            oid_pattern = re.compile(re.escape('.1.3.6.1.2.1.4.20.1.2.'))

            # Walk trough the IP-MIB::ipAdEntIfIndex tree. Results are in format:
            # .1.3.6.1.2.1.4.20.1.2.10.170.0.129 = INTEGER: 8
            # .1.3.6.1.2.1.4.20.1.2.10.170.1.1   = INTEGER: 10
            #       OID ends here-^|^- IP starts here       ^- ifIndex
            # etc...
            interface_address_results = self.session.walk('.1.3.6.1.2.1.4.20.1.2')
            self.logger.info("Device has %d IP addresses" % len(interface_address_results))
            for interface_address_result in interface_address_results:

                # IF-MIB::ifIndex later used to get IF-MIB::ifName
                if_index = int(interface_address_result.value)
                # If this is the first time encountering this ifIndex,
                # create DeviceInstance
                if if_index not in self.interfaces:
                    # Some devices will have loopback IP and ifIndex
                    # But no ifName associated with that ifIndex
                    # We can skip those since we can't make PTRs
                    try:
                        self.logger.debug("Create DeviceInterface object for ifIndex:%d" % if_index)
                        self.interfaces[if_index] = DeviceInterface(self, if_index)
                    except easysnmp.EasySNMPNoSuchInstanceError:
                        self.logger.warning("SNMP returned NOSUCHINSTANCE for ifIndex:%d" % if_index)
                        continue
                # Remove the part of the OID we used to walk on. Leave just the IP address part.
                # Add it to interface
                ip_address = '.'.join([
                    re.sub(oid_pattern, '', interface_address_result.oid),
                    interface_address_result.oid_index
                ])
                self.logger.debug("Found '%s' address on ifIndex:%d" % (self.host, if_index))

                # If there's HSRP VIP address on this interface add it to interface vip addresses
                # Pop removes the key from dict so we don't add the same list multiple times
                self.interfaces[if_index].add_vip_addresses(hsrp_addresses.pop(if_index, []))

                # Add polled IP to interface IP list
                self.interfaces[if_index].add_ip_address(ip_address)

            return True
        except easysnmp.EasySNMPError as e:
            self.logger.error("Failed to connect to '%s': %s" % (self.hostname, e))
            return False

    def _get_hsrp_addresses(self):
        """
        Walks through the CISCO-HSRP-MIB::cHsrpGrpVirtualIpAddr and fetches ip addresses used as VIPs.
        These should be ignored when making PTRs.
        :param snmp:
        :return:
        """

        hsrp_addresses = {}
        if not self.session:
            self.logger.error("Method %s called without initializing SNMP session first." % __name__)
            return hsrp_addresses

        # Compiled regexp pattern - ipAdEntIfIndex + important dot ;)
        oid_pattern = re.compile(re.escape(".1.3.6.1.4.1.9.9.106.1.2.1.1.11.")+"(\d+)")

        # Walk trough the CISCO-HSRP-MIB::cHsrpGrpVirtualIpAddr tree. Results are in format:
        # .1.3.6.1.4.1.9.9.106.1.2.1.1.11.151061087.607 = IpAddress: 109.122.98.1
        # .1.3.6.1.4.1.9.9.106.1.2.1.1.11.151061088.608 = IpAddress: 109.122.98.65
        #                 OID ends here-^|^-iFindex ^-HSRP group     ^- VIP IP address
        # etc...
        try:
            hsrp_address_results = self.session.walk('.1.3.6.1.4.1.9.9.106.1.2.1.1.11')
            self.logger.info("Device has %d VIP addresses" % len(hsrp_address_results))
            for hsrp_address_result in hsrp_address_results:
                vip_address = hsrp_address_result.value
                ifIndex_match = oid_pattern.match(hsrp_address_result.oid)
                if ifIndex_match:
                    ifIndex = int(ifIndex_match.group(1))
                    if ifIndex not in hsrp_addresses:
                        hsrp_addresses[ifIndex] = []
                    hsrp_addresses[ifIndex].append(vip_address)
                    self.logger.debug("HSRP group VIP address: %s (ifIndex#%s) - should be ignored" % (vip_address, ifIndex))
                else:
                    self.logger.warn("Regexp match failed on %s" % hsrp_address_result.oid)
        except easysnmp.EasySNMPNoSuchObjectError as e:
            self.logger.info("HSRP not supported on '%s', skipping..." % self.hostname)
        except easysnmp.EasySNMPNoSuchInstanceError as e:
            self.logger.info("HSRP not configured on '%s', skipping..." % self.hostname)
        except easysnmp.EasySNMPError as e:
            self.logger.error("Failed to fetch HSRP addresses from '%s': %s" % (self.hostname, e))
        return hsrp_addresses


    def check_ptrs(self):
        """
        Checks each IP address on the interface
        IP addresses that match A record are considered to be loopback addresses
        Those IPs have PTR pointing to device hostname rather than name in hostname-interface.domain.example format
        :return:
        """
        self.logger.debug("Check PTRs for %d interfaces" % len(self.interfaces))
        for interface in self.interfaces:
            self.interfaces[interface].check_ptr()

    def get_number_of_interfaces(self):
        """
        Return total number of interfaces on device
        :return:
        """
        self.logger.debug("Returned number of interfaces: %d" % len(self.interfaces))
        return len(self.interfaces)

    def get_number_of_ip_addresses(self):
        """
        Return total number of IP addresses on device
        :return:
        """
        num = 0
        for interface in self.interfaces:
            num += len(self.interfaces[interface].ip_addresses)
        self.logger.debug("Returned number of IP addresses: %d" % num)
        return num

    def get_ptrs(self):
        """
        Return dictionary of PTR records from all interfaces
        :return:
        """
        ptrs = {}
        for interface in self.interfaces:
            ptrs.update(self.interfaces[interface].get_ptrs())
        self.logger.debug("Returned number of PTRs from %d interfaces: %d" % (len(self.interfaces), len(ptrs)))
        return ptrs
