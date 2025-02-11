/*
 * Copyright (C) 2013 Apple Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY APPLE INC. ``AS IS'' AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL APPLE INC. OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 * OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
 */

#include "config.h"

#import "APICast.h"
#import "JSContextInternal.h"
#import "JSGlobalObject.h"
#import "JSValueInternal.h"
#import "JSVirtualMachineInternal.h"
#import "JSWrapperMap.h"
#import "JavaScriptCore.h"
#import "ObjcRuntimeExtras.h"
#import <wtf/HashSet.h>

#if JS_OBJC_API_ENABLED

@implementation JSContext {
    JSVirtualMachine *m_virtualMachine;
    JSGlobalContextRef m_context;
    JSWrapperMap *m_wrapperMap;
    HashCountedSet<JSValueRef> m_protectCounts;
}

@synthesize exception;
@synthesize exceptionHandler;

- (id)init
{
    return [self initWithVirtualMachine:[[[JSVirtualMachine alloc] init] autorelease]];
}

- (id)initWithVirtualMachine:(JSVirtualMachine *)virtualMachine
{
    self = [super init];
    if (!self)
        return nil;

    m_virtualMachine = [virtualMachine retain];
    m_context = JSGlobalContextCreateInGroup(getGroupFromVirtualMachine(virtualMachine), 0);
    m_wrapperMap = [[JSWrapperMap alloc] initWithContext:self];

    self.exception = nil;
    self.exceptionHandler = ^(JSContext *context, JSValue *exceptionValue) {
        context.exception = exceptionValue;
    };

    toJS(m_context)->lexicalGlobalObject()->m_apiData = self;
    return self;
}

- (JSValue *)evaluateScript:(NSString *)script
{
    JSValueRef exceptionValue = 0;
    JSStringRef scriptJS = JSStringCreateWithCFString((CFStringRef)script);
    JSValueRef result = JSEvaluateScript(m_context, scriptJS, 0, 0, 0, &exceptionValue);
    JSStringRelease(scriptJS);

    if (exceptionValue)
        return [self valueFromNotifyException:exceptionValue];

    return [JSValue valueWithValue:result inContext:self];
}

- (JSValue *)globalObject
{
    return [JSValue valueWithValue:JSContextGetGlobalObject(m_context) inContext:self];
}

+ (JSContext *)currentContext
{
    WTFThreadData& threadData = wtfThreadData();
    CallbackData *entry = (CallbackData *)threadData.m_apiData;
    return entry ? entry->context : nil;
}

+ (JSValue *)currentThis
{
    WTFThreadData& threadData = wtfThreadData();
    CallbackData *entry = (CallbackData *)threadData.m_apiData;

    if (!entry->currentThis)
        entry->currentThis = [[JSValue alloc] initWithValue:entry->thisValue inContext:[JSContext currentContext]];

    return entry->currentThis;
}

+ (NSArray *)currentArguments
{
    WTFThreadData& threadData = wtfThreadData();
    CallbackData *entry = (CallbackData *)threadData.m_apiData;

    if (!entry->currentArguments) {
        JSContext *context = [JSContext currentContext];
        size_t count = entry->argumentCount;
        JSValue * argumentArray[count];
        for (size_t i =0; i < count; ++i)
            argumentArray[i] = [JSValue valueWithValue:entry->arguments[i] inContext:context];
        entry->currentArguments = [[NSArray alloc] initWithObjects:argumentArray count:count];
    }

    return entry->currentArguments;
}

- (JSVirtualMachine *)virtualMachine
{
    return m_virtualMachine;
}

@end

@implementation JSContext(SubscriptSupport)

- (JSValue *)objectForKeyedSubscript:(id)key
{
    return [self globalObject][key];
}

- (void)setObject:(id)object forKeyedSubscript:(NSObject <NSCopying> *)key
{
    [self globalObject][key] = object;
}

@end

@implementation JSContext(Internal)

JSGlobalContextRef contextInternalContext(JSContext *context)
{
    return context->m_context;
}

- (void)dealloc
{
    toJS(m_context)->lexicalGlobalObject()->m_apiData = 0;

    HashCountedSet<JSValueRef>::iterator iterator = m_protectCounts.begin();
    HashCountedSet<JSValueRef>::iterator end = m_protectCounts.end();
    for (; iterator != end; ++iterator)
        JSValueUnprotect(m_context, iterator->key);

    [m_wrapperMap release];
    JSGlobalContextRelease(m_context);
    [m_virtualMachine release];
    [super dealloc];
}

- (void)notifyException:(JSValueRef)exceptionValue
{
    self.exceptionHandler(self, [JSValue valueWithValue:exceptionValue inContext:self]);
}

- (JSValue *)valueFromNotifyException:(JSValueRef)exceptionValue
{
    [self notifyException:exceptionValue];
    return [JSValue valueWithUndefinedInContext:self];
}

- (BOOL)boolFromNotifyException:(JSValueRef)exceptionValue
{
    [self notifyException:exceptionValue];
    return NO;
}

- (void)beginCallbackWithData:(CallbackData *)callbackData thisValue:(JSValueRef)thisValue argumentCount:(size_t)argumentCount arguments:(const JSValueRef *)arguments
{
    WTFThreadData& threadData = wtfThreadData();
    [self retain];
    CallbackData *prevStack = (CallbackData *)threadData.m_apiData;
    *callbackData = (CallbackData){ prevStack, self, [self.exception retain], thisValue, nil, argumentCount, arguments, nil };
    threadData.m_apiData = callbackData;
    self.exception = nil;
}

- (void)endCallbackWithData:(CallbackData *)callbackData
{
    WTFThreadData& threadData = wtfThreadData();
    self.exception = callbackData->preservedException;
    [callbackData->preservedException release];
    [callbackData->currentThis release];
    [callbackData->currentArguments release];
    threadData.m_apiData = callbackData->next;
    [self release];
}

- (void)protect:(JSValueRef)value
{
    // Lock access to m_protectCounts
    JSC::JSLockHolder lock(toJS(m_context));

    if (m_protectCounts.add(value).isNewEntry)
        JSValueProtect(m_context, value);
}

- (void)unprotect:(JSValueRef)value
{
    // Lock access to m_protectCounts
    JSC::JSLockHolder lock(toJS(m_context));

    if (m_protectCounts.remove(value))
        JSValueUnprotect(m_context, value);
}

- (JSValue *)wrapperForObject:(id)object
{
    // Lock access to m_wrapperMap
    JSC::JSLockHolder lock(toJS(m_context));
    return [m_wrapperMap wrapperForObject:object];
}

@end

WeakContextRef::WeakContextRef(JSContext *context)
{
    objc_initWeak(&m_weakContext, context);
}

WeakContextRef::~WeakContextRef()
{
    objc_destroyWeak(&m_weakContext);
}

JSContext * WeakContextRef::get()
{
    return objc_loadWeak(&m_weakContext);
}

void WeakContextRef::set(JSContext *context)
{
    objc_storeWeak(&m_weakContext, context);
}

#endif
