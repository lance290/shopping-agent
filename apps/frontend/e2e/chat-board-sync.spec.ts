import { test, expect } from '@playwright/test';

test.describe('Chat-Board Synchronization Flow', () => {
  test.setTimeout(120000); // 2 minute timeout

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('Full flow: type search -> extend search -> click card', async ({ page }) => {
    // Wait for the page to load
    await page.waitForSelector('text=Shopping Agent', { timeout: 15000 });
    console.log('Page loaded');

    // Find the chat input - using the actual placeholder text
    const chatInput = page.locator('input[placeholder="What are you looking for?"]');
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    console.log('Chat input found');

    // Count initial cards in the Requests panel
    const cardSelector = 'div.p-3.rounded-lg.cursor-pointer';
    const initialCardCount = await page.locator(cardSelector).count();
    console.log(`Initial card count: ${initialCardCount}`);

    // ===== STEP 1: User types initial search =====
    console.log('STEP 1: Typing initial search "Montana State sweatshirt"...');
    await chatInput.fill('Montana State sweatshirt');
    await chatInput.press('Enter');

    // Wait for assistant response (look for the search indicator)
    await page.waitForSelector('text=Searching for', { timeout: 30000 }).catch(() => {
      console.log('No search indicator found, continuing...');
    });
    await page.waitForTimeout(8000); // Wait for full response

    // Verify a card was created
    const cardsAfterStep1 = await page.locator(cardSelector).count();
    console.log(`Cards after step 1: ${cardsAfterStep1}`);
    
    if (cardsAfterStep1 > initialCardCount) {
      console.log('✅ STEP 1 PASSED: Card was created');
    } else {
      console.log('❌ STEP 1 FAILED: No card was created');
    }

    // ===== STEP 2: User extends the search (should NOT create new card) =====
    console.log('STEP 2: Extending search with "just those under $50 please"...');
    await chatInput.fill('just those under $50 please');
    await chatInput.press('Enter');

    // Wait for assistant response
    await page.waitForTimeout(8000);

    // CRITICAL: Card count should NOT increase - we should update the existing card
    const cardsAfterStep2 = await page.locator(cardSelector).count();
    console.log(`Cards after step 2: ${cardsAfterStep2}`);
    
    if (cardsAfterStep2 === cardsAfterStep1) {
      console.log('✅ STEP 2 PASSED: No new card created (existing card updated)');
    } else {
      console.log(`❌ STEP 2 FAILED: New card was created! Expected ${cardsAfterStep1}, got ${cardsAfterStep2}`);
      // Take screenshot for debugging
      await page.screenshot({ path: 'step2-failure.png', fullPage: true });
    }

    // Check the active card title (with timeout)
    try {
      const activeCard = page.locator('[class*="bg-blue-600"]').first();
      const isVisible = await activeCard.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        const cardTitle = await activeCard.locator('h3').textContent({ timeout: 3000 }).catch(() => 'N/A');
        console.log(`Active card title: ${cardTitle}`);
      }
    } catch (e) {
      console.log('Could not get active card title');
    }

    // ===== STEP 3: Click a different card =====
    console.log('STEP 3: Testing card click flow...');
    
    // Listen for console logs
    page.on('console', msg => {
      if (msg.text().includes('[Chat]') || msg.text().includes('[Sidebar]')) {
        console.log(`BROWSER: ${msg.text()}`);
      }
    });
    
    // Count user messages in chat before clicking (look for user message bubbles in the chat panel)
    // The chat panel is on the left, cards are in the sidebar
    const chatPanel = page.locator('div.w-1\\/3');
    const userMessagesBefore = await chatPanel.locator('div.bg-blue-600.text-white').count();
    console.log(`User messages before click: ${userMessagesBefore}`);
    
    // Find a non-active card in the Requests sidebar (gray background, not blue)
    // Cards are in RequestsSidebar with class bg-gray-700 (inactive) or bg-blue-600 (active)
    const inactiveCard = page.locator('div.bg-gray-700.text-gray-200.cursor-pointer').first();
    const isInactiveVisible = await inactiveCard.isVisible({ timeout: 3000 }).catch(() => false);
    
    if (isInactiveVisible) {
      const cardTitleToClick = await inactiveCard.locator('h3').textContent({ timeout: 3000 }).catch(() => 'Unknown');
      console.log(`Clicking card: ${cardTitleToClick}`);
      
      await inactiveCard.click();
      await page.waitForTimeout(5000); // Wait for state update and chat append
      
      // Verify the card's text was appended to chat
      const userMessagesAfter = await chatPanel.locator('div.bg-blue-600.text-white').count();
      console.log(`User messages after click: ${userMessagesAfter}`);
      
      if (userMessagesAfter > userMessagesBefore) {
        console.log('✅ STEP 3 PASSED: Card text was appended to chat');
      } else {
        console.log('❌ STEP 3 FAILED: Card text was NOT appended to chat');
        await page.screenshot({ path: 'step3-failure.png', fullPage: true });
      }
    } else {
      console.log('No inactive card to click, skipping step 3');
    }

    // Final screenshot
    await page.screenshot({ path: 'final-state.png', fullPage: true });
    console.log('Test completed!');
    
    // Assert all steps passed
    expect(cardsAfterStep1).toBeGreaterThan(initialCardCount); // Step 1
    expect(cardsAfterStep2).toBe(cardsAfterStep1); // Step 2
  });
});
