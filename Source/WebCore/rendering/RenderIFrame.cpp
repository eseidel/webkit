/*
 * Copyright (C) 2010 Apple Inc. All rights reserved.
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
 * THIS SOFTWARE IS PROVIDED BY APPLE COMPUTER, INC. ``AS IS'' AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL APPLE COMPUTER, INC. OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 * OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
 */

#include "config.h"
#include "RenderIFrame.h"

#include "Frame.h"
#include "FrameView.h"
#include "HTMLIFrameElement.h"
#include "HTMLNames.h"
#include "Page.h"
#include "RenderView.h"
#include "Settings.h"

namespace WebCore {

using namespace HTMLNames;
    
RenderIFrame::RenderIFrame(Element* element)
    : RenderFrameBase(element)
{
}

void RenderIFrame::computeLogicalHeight()
{
    RenderPart::computeLogicalHeight();
    if (!flattenFrame())
         return;

    HTMLIFrameElement* frame = static_cast<HTMLIFrameElement*>(node());
    bool isScrollable = frame->scrollingMode() != ScrollbarAlwaysOff;

    if (isScrollable || !style()->height().isFixed()) {
        FrameView* view = static_cast<FrameView*>(widget());
        if (!view)
            return;
        LayoutUnit border = borderTop() + borderBottom();
        setHeight(max<LayoutUnit>(height(), view->contentsHeight() + border));
    }
}

void RenderIFrame::computeLogicalWidth()
{
    // When we're seamless, we behave like a block.  Thankfully RenderBox has all the right logic for this.
    if (isSeamless())
        return RenderBox::computeLogicalWidth();

    RenderPart::computeLogicalWidth();
    if (!flattenFrame())
        return;

    HTMLIFrameElement* frame = static_cast<HTMLIFrameElement*>(node());
    bool isScrollable = frame->scrollingMode() != ScrollbarAlwaysOff;

    if (isScrollable || !style()->width().isFixed()) {
        FrameView* view = static_cast<FrameView*>(widget());
        if (!view)
            return;
        LayoutUnit border = borderLeft() + borderRight();
        setWidth(max<LayoutUnit>(width(), view->contentsWidth() + border));
    }
}

bool RenderIFrame::shouldComputeSizeAsReplaced() const
{
    // When we're seamless, we use normal block/box sizing code except when inline.
    return !isSeamless();
}

bool RenderIFrame::isInlineBlockOrInlineTable() const
{
    return isSeamless() && isInline();
}

LayoutUnit RenderIFrame::minPreferredLogicalWidth() const
{
    if (!isSeamless())
        return RenderFrameBase::minPreferredLogicalWidth();

    RenderView* childRoot = contentRootRenderer();
    if (!childRoot)
        return 0;

    return childRoot->minPreferredLogicalWidth();
}

LayoutUnit RenderIFrame::maxPreferredLogicalWidth() const
{
    if (!isSeamless())
        return RenderFrameBase::maxPreferredLogicalWidth();

    RenderView* childRoot = contentRootRenderer();
    if (!childRoot)
        return 0;

    return childRoot->maxPreferredLogicalWidth();
}

bool RenderIFrame::isSeamless() const
{
    return node() && node()->hasTagName(iframeTag) && static_cast<HTMLIFrameElement*>(node())->shouldDisplaySeamlessly();
}

RenderView* RenderIFrame::contentRootRenderer() const
{
    // FIXME: Is this always a valid cast?  What about plugins?
    FrameView* childFrameView = static_cast<FrameView*>(widget());
    return childFrameView ? static_cast<RenderView*>(childFrameView->frame()->contentRenderer()) : 0;
}

bool RenderIFrame::flattenFrame() const
{
    if (!node() || !node()->hasTagName(iframeTag))
        return false;

    HTMLIFrameElement* element = static_cast<HTMLIFrameElement*>(node());
    Frame* frame = element->document()->frame();

    if (isSeamless())
        return false; // Seamless iframes are already "flat", don't try to flatten them.

    bool enabled = frame && frame->settings() && frame->settings()->frameFlatteningEnabled();

    if (!enabled || !frame->page())
        return false;

    if (style()->width().isFixed() && style()->height().isFixed()) {
        // Do not flatten iframes with scrolling="no".
        if (element->scrollingMode() == ScrollbarAlwaysOff)
            return false;
        if (style()->width().value() <= 0 || style()->height().value() <= 0)
            return false;
    }

    // Do not flatten offscreen inner frames during frame flattening, as flattening might make them visible.
    IntRect boundingRect = absoluteBoundingBoxRectIgnoringTransforms();
    return boundingRect.maxX() > 0 && boundingRect.maxY() > 0;
}

void RenderIFrame::layout()
{
    ASSERT(needsLayout());

    if (flattenFrame()) {
        RenderPart::computeLogicalWidth();
        RenderPart::computeLogicalHeight();
        layoutWithFlattening(style()->width().isFixed(), style()->height().isFixed());
        // FIXME: Is early return really OK here? What about transform/overflow code below?
        return;
    }

    computeLogicalWidth();
    // The 3 main phases of layout are: 1. Compute width, 2. Layout kids, 3. Compute height.
    // For Seamless iframes, our "kids" are the subframe, so we layout the subframe synchronously here.
    if (isSeamless()) {
        setHeight(0); // Clear our height before laying out our kids.
        updateWidgetPosition(); // Tell the Widget about our new Width/Height.

        FrameView* childFrameView = static_cast<FrameView*>(widget());
        childFrameView->layout();

        // Laying out our kids is normally responsible for adjusting our height, so we set it here.
        // Replaced elements do not respect padding, so we just add border to the child's height.
        setHeight(childFrameView->contentsHeight() + borderTop() + borderBottom());
    }

    // Once our kids have determined our height we actually apply min/max to our height.
    computeLogicalHeight();

    if (isSeamless()) {
        updateWidgetPosition(); // Notify the Widget of our final height.

        FrameView* childFrameView = static_cast<FrameView*>(widget());
        RenderView* childRoot = childFrameView ? static_cast<RenderView*>(childFrameView->frame()->contentRenderer()) : 0;

        ASSERT(!childFrameView->layoutPending());
        ASSERT(!childRoot->needsLayout());
        ASSERT(!childRoot->firstChild() || !childRoot->firstChild()->firstChild() || !childRoot->firstChild()->firstChild()->needsLayout());
    }

    m_overflow.clear();
    addVisualEffectOverflow();
    updateLayerTransform();

    setNeedsLayout(false);
}

}
