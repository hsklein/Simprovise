#===============================================================================
# MODULE agent
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimAgent and SimMessage classes.  (SimAgents send and receive
# messages derived from the SimMessage class)
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
from collections import deque, namedtuple
from contextlib import contextmanager

from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging
from simprovise.core.model import SimModel
from simprovise.core.apidoc import apidoc, apidocskip
from simprovise.core.apidoc import generating_docs

logger = SimLogging.get_logger(__name__)

_MESSAGE_HANDLING_ERROR = "SimMessage Handling Error"

SimMessage = namedtuple('SimMessage',
                        'msgID msgType sendTime sender receiver originatingMsg msgData')

# Hack to generate documentation for SimMessage - turn it into a regular class.
# http://stackoverflow.com/questions/13785150/how-can-i-provide-sphinx-documentation-for-a-namedtuple-with-autodoc
# We may not want this to happen in actual production, so we'll just define the
# class while generating documentation.
if generating_docs:
    @apidoc
    class SimMessage(SimMessage):
        """
        SimMessages encapsulate a message sent from one SimAgent to another.
        It is a namedtuple; its members are:

        * msgID: A unique sequence number identifier for the message
        * msgType: One of the :class:`SimMsgType` strings 
        * sendTime: A :class:`~.simtime.SimTime` representing the
                simulated time the message was sent
        * sender: The sending :class:`SimAgent`
        * receiver: The recipient :class:`SimAgent`
        * originatingMsg: The msgID of the message to which this is a response
          (or None, if not a response)
        * msgData: One or more data items/objects, based on message type

        SimMessages are created only by :class:`SimAgent` objects, via methods
        :meth:`.send_message` and :meth:`.send_response`. Client code should
        always use one of those methods (directly or indirectly) to send
        messages.
        
        """

_msgcount = 0
def _next_msgID():
    global _msgcount
    _msgcount += 1
    return _msgcount

@apidoc
class SimMsgType(object):
    """
    Basically, a namespace of message types.
    TODO Should this be an Enum?
    """
    RSRC_REQUEST = "ResourceRequest"
    RSRC_ASSIGNMENT = "ResourceAssignment"
    RSRC_RELEASE = "ResourceRelease"
    #RSRC_TAKEDOWN_REQ = "ResourceTakeDownRequest"
    #RSRC_BRINGUP_REQ = "ResourceBringUpRequest"
    RSRC_DOWN = "ResourceDown"
    RSRC_GOING_DOWN = "ResourceGoingDown"
    RSRC_UP = "ResourceUp"
    #LOC_REQUEST = "LocationRequest"
    #LOC_ASSIGNMENT = "LocationAssignment"
    #LOC_RELEASE = "LocationRelease"


@apidoc
class SimAgent(object):
    """
    ``SimAgent`` provides the basic framework for agent-like behavior. In
    particular, it provides the functionality required to send, receive and
    process messages, both synchronously and asynchronously. SimAgents
    (and the instances of classes derived from SimAgent) are the only objects
    that send messages, and are the only objects allowed to receive them.
    
    While most messages are sent to a single specified receiver, SimAgent
    also implements a message subscription service, that allows any agent
    to subscribe to messages sent by another agent of a specified 
    message type; those agents (who subscribe via :meth:`add_subscriber`)
    will receive subscribed-to messages at the same time they are sent
    to the originally specified receiver.
    
    SimAgent is a base class for almost all of the modeling classes.
    Modeling code should never instantiate A SimAgent directly, and
    probably will never need to subclass it directly; more typically,
    the modeler will subclass SimAgent subclasses such as
    :class:`~.resource.SimResource` or :class:`~.process.SimProcess`.

    """
    #agents = set()
    
    @staticmethod
    def final_initialize_all():
        """
        Invoke :meth:`final_initialize` on all agents
        """
        for agent in SimModel.model().agents:
            agent.final_initialize()
    
    def __init__(self):
        """
        """
        # For now, we'll just use a deque for FIFO message processing.
        # TODO the optimal data structure will vary based on the agent (e.g., a
        # deque would be best in many, but not all cases).  If necessary, we
        # can look at providing that flexibility.
        self.msg_queue = deque()
        self.interceptHandler = None
        # _msgTypeHandler is a dictionary of functions and/or methods that
        # handle messages of a specific message type or types.  The dictionary
        # is keyed by message type, and thus used to dispatch messages to
        # the correct handler.
        self._msgTypeHandler = {}

        # _msgPriorityFunc is a dictionary of functions that determine and
        # return a priority for message of a specified message type or types.
        # The dictionary is keyed by message type, and used by
        # nextQueuedMessage()
        self._msgPriorityFunc = {}
        
        # _subscribers is a dictionary of sets of agents, keyed by message
        # type. These subscribers are agents wishing receive *every* message
        # sent by this agent of a given message type.
        self._subscribers = {}
        
        # Add this agent to the model-maintained set of agents
        SimModel.model()._register_agent(self)
        
    def final_initialize(self):
        """
        Do any last-minute initialization as simulation execution is about
        to begin. Typically implemented for agents that require initialization
        after the SimClock SimEventProcessor, and/or random number streams
        are created/initialized.
        
        Default is a no-op
        """
        pass
    
    def add_subscriber(self, subscriber, msgType):
        """
        Add an agent to the set of subscribers to a specified message type.
        A subscriber will receive (as a monitor/listener) **every** message
        of the specified type sent by this agent whoe receipient is a
        different agent.
        
        Messages received by subscription are dispatched like regular
        messages, but are never queued and should not be responded-to.
        
        :param subscriber: Agent subscribing
        :type subscriber:  :class:`SimAgent`
        
        :param msgType:    The message type being subscribed to
        :type msgType:     :class:`SimMsgType`
        
        """
        assert subscriber, "null subscriber passed to add_subscriber()"
        assert subscriber is not self, "An agent can't subscribe to itself"
        assert msgType, "null msgType passed to add_subscriber()"
        assert isinstance(subscriber, SimAgent), "only SimAgents can subscribe"       
        self._subscribers.setdefault(msgType, set()).add(subscriber)
        
    def _notify_subscribers(self, msg):
        """
        Send the passed message to all agents subscribing to that message's
        message type.
        
        Called by send_message/send_response
        """
        msgType = msg.msgType
        receiver = msg.receiver
        
        if msgType in self._subscribers:           
            subscribers = self._subscribers[msgType]
            for subscriber in subscribers:
                if subscriber is not receiver:
                    subscriber.receive_subscribed_message(msg)

    def send_message(self, toAgent, msgType, msgData, msgClass=None):
        """
        Send a SimMessage-derived message to a specified recipient.  Returns
        both the sent message and any immediate responses.  (If there are no
        immediate responses, the returned responses list is empty.)

        Note that the returned responses are the responsibility of the caller
        to act upon; they are gathered (by a response interceptor) before the
        agent's designated message handler can act on them. In other words,
        agent code that calls sendMessage() should be be prepared to deal
        with both an immediate response (sent as part of the return value to
        sendMessage()) or a later asynchronous response which will be
        delegated to one of the agent's message handler based on the
        :class:`.SimMsgType` of the response.
       
        :param toAgent: Agent which is the target/recipient of the message
        :type toAgent: :class:`SimAgent`
       
        :param msgType: The message type
        :type msgType:  :class:`SimMsgType`
       
        :param msgData: Message content
        :type msgData:  Varies by message type

        :return:        The message created and sent by this call and a list
                        of any response messages sent immediately by the message
                        recipient (which may be empty, if the recipient did not
                        immediately respond)
        :rtype:         tuple (sent message, list of response messages)
             
        """
        assert toAgent, "Null toAgent (recipient) argument to sendMessage()"
        assert msgType, "Null msgType argument to sendMessage()"
        assert msgClass is None or issubclass(msgClass, SimMessage), "msgClass is not a subclass of SimMessage"

        if msgClass is None:
            msgClass = SimMessage
            
        @contextmanager
        def intercept_responses(toMsg):
            """
            Sets an intercept handler on this agent that intercepts and
            collects any responses to the passed message (preventing them
            from being handled by the agents handleMessage() method) and
            returns them in a list.

            This supports the notion that if an agent sends a message, any
            immediate responses to that message should be part of the return
            value from the sendMessage() call.

            Implemented as a context manager so that this agent's intercept
            handler can be returned to its original state after leaving the
            context.
            
            """
            responses = []
            def handler(msg):
                if msg.originatingMsg == toMsg:
                    responses.append(msg)
                    return True
                else:
                    return False
            savedHandler = self.interceptHandler
            self.interceptHandler = handler
            yield responses
            self.interceptHandler = savedHandler

        msg = msgClass(_next_msgID(), msgType, SimClock.now(), self, toAgent,
                       None, msgData)
        with intercept_responses(msg) as responses:
            toAgent.receive_message(msg)
            
        self._notify_subscribers(msg)
        return msg, responses

    def send_response(self, originatingMsg, msgType, msgData):
        """
        Send a specified message (responseMsg) in response to a received
        (originating) message. The response is sent to the originating
        message's sender.
        
        :param originatingMsg: The message being responded to
        :type originatingMsg:  :class:`SimMessage`
       
        :param msgType:        The message type
        :type msgType:         :class:`SimMsgType`
       
        :param msgData:        Message content
        :type msgData:         Varies by message type
                                         
        """
        assert originatingMsg, "Null originatingMsg argument to sendResponse()"
        assert msgType, "Null msgType argument to sendResponse()"
        assert originatingMsg.receiver == self, "originatingMsg argument to sendResponse() was not sent to this agent"

        toAgent = originatingMsg.sender
        responseMsg = SimMessage(_next_msgID(), msgType, SimClock.now(), self,
                                 toAgent, originatingMsg, msgData)
        toAgent.receive_message(responseMsg)
        self._notify_subscribers(responseMsg)

    @apidocskip
    def receive_message(self, msg):
        """
        Receive a new message.
        If this agent has a currently designated message interceptor, give that
        interceptor first crack at handling the message.  If there is no
        interceptor (or the interceptor chooses not to handle the message),
        then delegate to the agent's default handleMessage() method.

        If at the end of all this, the message has still not been handled, add
        it to the message queue for later processing.

        TODO consider a handler chain, with multiple interceptors?
        """
        assert msg, "Null msg argument to receive_message()"
        assert msg.receiver is self, "msg recipient does not match agent processing receive_message()"
        assert msg.originatingMsg is None or msg.originatingMsg.sender is self, "msg is a response to an agent other than the agent processing receive_message()"

        if self.interceptHandler and self.interceptHandler(msg):
            handled = True
        else:
            handled = self._dispatch_message(msg)
        if not handled:
            self.msg_queue.append(msg)

    @apidocskip
    def receive_subscribed_message(self, msg):
        """
        Receive a message that this agent has subscribed to (but is not
        the recipient/receiver of the message).
        
        As a subscriber/observer, just dispatch the message to a handler;
        subscribed messages never get queued.
        """
        assert msg, "Null msg argument to receive_subscribed_message()"
        assert msg.receiver is not self, "msg recipient should NOT match agent processing receive_subscribed_message()"
        self._dispatch_message(msg)

    def _dispatch_message(self, msg):
        """
        Dispatch the passed message to the handler registered for its message
        type. The handler should return True if the message was handled,
        False if the message was not handled (and should therefore be
        enqueued). _dispatchMessage() returns the value returned by the
        handler; if no handler is registered for the message type, an error
        is raised.

        Handler functions/methods are registered via the registerHandler()
        method.
        
        """
        msgType = msg.msgType
        if msgType in self._msgTypeHandler:
            return self._msgTypeHandler[msgType](msg)
        else:
            errorMsg = "Unexpected message type of {0} sent to {1}"
            raise SimError(_MESSAGE_HANDLING_ERROR, errorMsg, msgType,
                           self.__class__.__name__)

    def register_handler(self, msgType, handler):
        """
        Register the passed handler function/method to handle messages of the
        passed msgType.

        The handler function should take one parameter (of type
        :class:`SimMessage`) and return True or False (depending on whether
        it was handled or not.)

        If there is an existing handler for the specified message type, it
        will be replaced by the more recently registered handler - there is
        not, at this time, any notion of handler chains.
       
        :param msgType: The message type to be processed by this handler
        :type msgType:  :class:`SimMsgType`
       
        :param handler: Handler function
        :type handler:  function
            
        """
        assert msgType, "null message type passed to registerHandler()"
        assert callable(handler), "handler passed to registerHandler() is not a callable"
        self._msgTypeHandler[msgType] = handler

    def register_priority_func(self, msgType, func):
        """
        Register a function that returns a priority (lowest value is highest
        priority) to a message. This function will be applied only to messages
        of the specified type. The function should take a SimMessage as its
        sole argument. If two messages have identical priority, the oldest
        message wins.

        Used to prioritize queued messages of a specific type. Note that
        prioritization can be dynamic - i.e., the priority of a message can
        change over time as (simulated) circumstances change.
       
        :param msgType: Type of messages prioritized by the passed function
        :type msgType:  :class:`SimMsgType`
       
        :param func:    Priority function as described above
        :type func:     function
            
        """
        assert msgType, "null message type passed to registerPriorityFunc()"
        assert callable(func), "function passed to registerPriorityFunc() is not a callable"
        self._msgPriorityFunc[msgType] = func

    def priority_func(self, msgType):
        """
        Returns the registered priority function for the specified message
        type (or None if nothing is registered for that type)
       
        :param msgType: The message type for which we are getting the
                        registered priority function.
        :type msgType:  :class:`SimMsgType`
        
         :return:       The priority function associated with msgType
        :rtype:         func
         
        """
        if msgType in self._msgPriorityFunc:
            return self._msgPriorityFunc[msgType]
        else:
            return None

    def queued_messages(self, msgType):
        """
        Returns a list of messages of the specified type from the agent's
        message queue. If a priority function is specified for that message
        type, the returned list is sorted in priority order (ties are FIFO).
        Does NOT remove any messages from the queue.

        If there are NO queued messages of the specified type, returns an
        empty list.

        :param msgType: The type of message desired
        :type msgType: :class:`SimMsgType`

        :return:       A new list of queued message of type msgType, 
                       sorted by priority, or FIFO, if no priority
                       function has been registered for msgType. e)
        :rtype:        `list` of :class:`SimMessage`
                        
        """
        msgs = [msg for msg in self.msg_queue if msg.msgType == msgType]
        if msgType in self._msgPriorityFunc:
            msgs.sort(key=self._msgPriorityFunc[msgType])
        return msgs

    def next_queued_message(self, msgType):
        """
        Returns the next request message of the specified type from the agent's
        message queue. If a priority function is specified for that message
        type, the queue is prioritized - i.e., we return the first message with
        the highest (minimum) priority value as determined by the priority
        function. Does NOT remove the message from the queue.

        If there are NO queue messages of the specified type, returns None.

        :param msgType: The type of message desired
        :type msgType: :class:`SimMsgType`

        :return:       The queued message of type msgType with the highest
                        priority, or the oldest message, if no priority
                        function has been registered for msgType. (or None
                        if there are no queued messages of type msgType)
        :rtype:        :class:`SimMessage`
                        
        """
        msgs = [msg for msg in self.msg_queue if msg.msgType == msgType]
        if len(msgs) == 0:
            return None
        elif msgType in self._msgPriorityFunc:
            return min(msgs, key=self._msgPriorityFunc[msgType])
        else:
            return msgs[0]

    def message_priority(self, msg):
        """
        Return the priority of a passed message - if there is a priority
        function registered for that message's type. If not, return None.
         
        :param msg:       The message whose priority is being queried
        :type SimMessage: :class:`SimMessage`

        :return:          The priority of msg, or None if no priority
                          function is registered for msg's message type.
        :rtype:           int or None
       
        """
        if msg.msgType in self._msgPriorityFunc:
            return self._msgPriorityFunc[msg.msgType](msg)
        else:
            return None




if __name__ == '__main__':
    class TestAgent(SimAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.register_handler("TestType", self.handleMessage)
            
        def handleMessage(self, msg):
            "R"
            remainder = msg.msgID % 3
            if remainder == 0:
                return False
            elif remainder == 1:
                self.send_response(msg, "TestResponseType", "Response to {0}".format(msg.msgID))
                return True
            else:
                print("handling message", msg.msgID, msg.content)
                return True

    agent1 = SimAgent()
    agent2 = TestAgent()

    msg1, responses = agent1.send_message(agent2, "TestType", "Test Data")
    print(msg1)
    print("Responses")
    for r in responses:
        print(r)
    print("agent 2 message queue")
    for r in agent2.msg_queue:
        print(r)
