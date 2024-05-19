#===============================================================================
# MODULE agent
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimAgent and SimMessage classes.  (SimAgents send and receive
# messages derived from the SimMessage class)
#===============================================================================
from collections import deque, namedtuple
from contextlib import contextmanager

from simprovise.core import (SimError, SimClock, SimLogging)
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
    RSRC_TAKEDOWN = "ResourceTakeDown"
    RSRC_BRINGUP = "ResourceBringUp"
    LOC_REQUEST = "LocationRequest"
    LOC_ASSIGNMENT = "LocationAssignment"
    LOC_RELEASE = "LocationRelease"


@apidoc
class SimAgent(object):
    """
    SimAgent provides the basic framework for agent-like behavior. In
    particular, it provides the functionality required to send, receive and
    process messages, both synchronously and asynchronously. SimAgents
    (and the instances of classes derived from SimAgent) are the only objects
    that send messages, and are the only objects allowed to receive  them.
    
    SimAgent is a base class for almost all of the modeling classes.
    Modeling code should never instantiate A SimAgent directly, and
    probably will never need to subclass it directly; more typically,
    the modeler will subclass SimAgent subclasses such as
    :class:`~.resource.SimResource` or :class:`~.process.SimProcess`.

    """
    def __init__(self):
        """
        """
        # For now, we'll just use a deque for FIFO message processing.
        # TODO the optimal data structure will vary based on the agent (e.g., a
        # deque would be best in many, but not all cases).  If necessary, we
        # can look at providing that flexibility.
        self.msgQueue = deque()
        self.interceptHandler = None
        # _msgTypeHandler is a dictionary of functions and/or methods that
        # handle messages of a specific message type or types.  The dictionary
        # is keyed by message type, and thus used to dispatch messages to
        # the correct handler.
        self._msgTypeHandler = {}

        # _msgPriorityFunc is a dictionary of functions that determine and
        # return a priority for message of a specified message type or types.
        # The dictionary is keyed by message type, and used by
        #nextQueuedMessage()
        self._msgPriorityFunc = {}

    def send_message(self, toAgent, msgType, msgData):
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

         :return:       The message created and sent by this call and a list
                        of any response messages sent immediately by the message
                        recipient (which may be empty, if the recipient did not
                        immediately respond)
        :rtype:         tuple (sent message, list of response messages)
             
        """
        assert toAgent, "Null toAgent (recipient) argument to sendMessage()"
        assert msgType, "Null msgType argument to sendMessage()"

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

        msg = SimMessage(_next_msgID(), msgType, SimClock.now(), self, toAgent,
                         None, msgData)
        with intercept_responses(msg) as responses:
            toAgent.receive_message(msg)
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
        assert msg, "Null msg argument to receiveMessage()"
        assert msg.receiver is self, "msg recipient does not match agent processing receiveMessage()"
        assert msg.originatingMsg is None or msg.originatingMsg.sender is self, "msg is a response to an agent other than the agent processing receiveMessage()"

        if self.interceptHandler and self.interceptHandler(msg):
            handled = True
        else:
            handled = self._dispatch_message(msg)
        if not handled:
            self.msgQueue.append(msg)

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
        msgs = [msg for msg in self.msgQueue if msg.msgType == msgType]
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
        msgs = [msg for msg in self.msgQueue if msg.msgType == msgType]
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
    for r in agent2.msgQueue:
        print(r)
