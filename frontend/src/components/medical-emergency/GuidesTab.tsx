/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { AlertTriangle, Heart, Zap, Home, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslation } from '@/i18n';

function CPRGuideSection() {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full font-semibold text-lg text-earth-900 hover:text-lsc-rose dark:text-lsc-rose-light"
      >
        <div className="flex items-center gap-3">
          <Heart className="w-6 h-6" />
          CPR Guide - Chest Compressions & Rescue Breathing
        </div>
        {expanded ? <ChevronUp /> : <ChevronDown />}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 text-sm">
          <div>
            <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-2">STEP 1: Check Responsiveness</h4>
            <ul className="list-disc list-inside space-y-1 text-earth-800 dark:text-lsc-rose-light">
              <li>{t('staffMedicalEmergency.tapShouldersAndShoutAre')}</li>
              <li>{t('staffMedicalEmergency.checkForNormalBreathingMax')}</li>
              <li>{t('staffMedicalEmergency.ifNoResponseBeginCpr')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-2">{t('staffMedicalEmergency.stepPositionThePerson')}</h4>
            <ul className="list-disc list-inside space-y-1 text-earth-800 dark:text-lsc-rose-light">
              <li>{t('staffMedicalEmergency.placeOnFirmFlatSurface')}</li>
              <li>{t('staffMedicalEmergency.ensureAirwayIsClearRemove')}</li>
              <li>{t('staffMedicalEmergency.tiltHeadBackSlightlyTo')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-2">{t('staffMedicalEmergency.stepHandPositionForCompression')}</h4>
            <ul className="list-disc list-inside space-y-1 text-earth-800 dark:text-lsc-rose-light">
              <li>{t('staffMedicalEmergency.placeHeelOfOneHand')}</li>
              <li>{t('staffMedicalEmergency.placeOtherHandOnTop')}</li>
              <li>{t('staffMedicalEmergency.keepArmsStraightElbowsLocked')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-2">STEP 4: Chest Compressions</h4>
            <ul className="list-disc list-inside space-y-1 text-earth-800 dark:text-lsc-rose-light">
              <li>{t('staffMedicalEmergency.pushHardAndFastAt')}</li>
              <li>{t('staffMedicalEmergency.rateCompressionsPerMinuteThink')}</li>
              <li>{t('staffMedicalEmergency.allowChestToFullyRecoil')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-2">{t('staffMedicalEmergency.stepRescueBreathingRatio')}</h4>
            <ul className="list-disc list-inside space-y-1 text-earth-800 dark:text-lsc-rose-light">
              <li>{t('staffMedicalEmergency.afterCompressionsGiveRescueBreaths')}</li>
              <li>{t('staffMedicalEmergency.pinchNoseSealMouthBlow')}</li>
              <li>{t('staffMedicalEmergency.watchForChestRiseRepeat')}</li>
              <li>{t('staffMedicalEmergency.continueUntilAedIsApplied')}</li>
            </ul>
          </div>

          <div className="bg-earth-100 dark:bg-earth-800/30 p-3 rounded border-l-4 border-lsc-rose mt-4">
            <p className="font-semibold text-earth-900 dark:text-lsc-rose-light/80">⏱️ Continue CPR until:</p>
            <ul className="list-disc list-inside mt-2 text-earth-800 dark:text-lsc-rose-light text-xs">
              <li>{t('staffMedicalEmergency.personStartsBreathingMoving')}</li>
              <li>{t('staffMedicalEmergency.aedArrivesAndIsApplied')}</li>
              <li>{t('staffMedicalEmergency.emergencyRespondersTakeOver')}</li>
              <li>{t('staffMedicalEmergency.youAreExhaustedRotateWith')}</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function AEDGuideSection() {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full font-semibold text-lg text-status-warning-900 hover:text-status-warning-700 dark:text-status-warning-300"
      >
        <div className="flex items-center gap-3">
          <Zap className="w-6 h-6" />
          AED Defibrillator Instructions
        </div>
        {expanded ? <ChevronUp /> : <ChevronDown />}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 text-sm">
          <div>
            <h4 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200 mb-2">{t('staffMedicalEmergency.stepRetrieveTheAed')}</h4>
            <ul className="list-disc list-inside space-y-1 text-status-warning-800 dark:text-status-warning-300">
              <li>{t('staffMedicalEmergency.locateNearestAedSeeLocations')}</li>
              <li>{t('staffMedicalEmergency.checkSignagePublicAedsAre')}</li>
              <li>{t('staffMedicalEmergency.ifLockedBreakGlassOr')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200 mb-2">{t('staffMedicalEmergency.stepPrepareThePerson')}</h4>
            <ul className="list-disc list-inside space-y-1 text-status-warning-800 dark:text-status-warning-300">
              <li>{t('staffMedicalEmergency.removeClothingFromChestCut')}</li>
              <li>{t('staffMedicalEmergency.dryChestIfWetSweaty')}</li>
              <li>{t('staffMedicalEmergency.removeAnyMedicationPatchesOr')}</li>
              <li>{t('staffMedicalEmergency.ifPersonHasPacemakerDefibrillator')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200 mb-2">STEP 3: Apply Pads</h4>
            <ul className="list-disc list-inside space-y-1 text-status-warning-800 dark:text-status-warning-300">
              <li>{t('staffMedicalEmergency.turnOnAedOpensAutomatically')}</li>
              <li>{t('staffMedicalEmergency.removePadBackingAndApply')}</li>
              <li>{t('staffMedicalEmergency.rightPadUpperRightChest')}</li>
              <li>{t('staffMedicalEmergency.leftPadLowerLeftSide')}</li>
              <li>{t('staffMedicalEmergency.pressFirmlyToEnsureContact')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200 mb-2">STEP 4: Analyze & Shock</h4>
            <ul className="list-disc list-inside space-y-1 text-status-warning-800 dark:text-status-warning-300">
              <li>{t('staffMedicalEmergency.donTTouchPersonWhile')}</li>
              <li>{t('staffMedicalEmergency.ifShockAdvisedDisplayed')}</li>
              <li>{t('staffMedicalEmergency.sayClearEnsureNoOne')}</li>
              <li>{t('staffMedicalEmergency.pressShockButtonFirmly')}</li>
              <li>{t('staffMedicalEmergency.continueCprImmediatelyAfterShock')}</li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200 mb-2">STEP 5: Continue Protocol</h4>
            <ul className="list-disc list-inside space-y-1 text-status-warning-800 dark:text-status-warning-300">
              <li>{t('staffMedicalEmergency.followAedVoicePrompts')}</li>
              <li>{t('staffMedicalEmergency.continueCprBetweenShocksMinutes')}</li>
              <li>{t('staffMedicalEmergency.aedWillPromptToCheck')}</li>
              <li>{t('staffMedicalEmergency.donTRemovePadsUntil')}</li>
            </ul>
          </div>

          <div className="bg-status-warning-100 dark:bg-status-warning-900/30 p-3 rounded border-l-4 border-status-warning-600 mt-4">
            <p className="font-semibold text-status-warning-900 dark:text-status-warning-200">⚡ Critical Points:</p>
            <ul className="list-disc list-inside mt-2 text-status-warning-800 dark:text-status-warning-300 text-xs space-y-1">
              <li>{t('staffMedicalEmergency.aedIsEasyToUse')}</li>
              <li>{t('staffMedicalEmergency.doesnTHarmIfPerson')}</li>
              <li>{t('staffMedicalEmergency.shouldNotBeUsedOn')}</li>
              <li>{t('staffMedicalEmergency.callBeforeApplyingAedIf')}</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function FirstAidBasicsSection() {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full font-semibold text-lg text-status-success-900 hover:text-status-success-700 dark:text-status-success-300"
      >
        <div className="flex items-center gap-3">
          <Home className="w-6 h-6" />
          First Aid Kit Essentials
        </div>
        {expanded ? <ChevronUp /> : <ChevronDown />}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 text-sm">
          <div>
            <h4 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200 mb-2">{t('staffMedicalEmergency.basicFirstAidKitContents')}</h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Bandages & Gauze</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">{t('staffMedicalEmergency.multipleSizesForWoundCovering')}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Antiseptic Wipes</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">{t('staffMedicalEmergency.cleanAndDisinfectWounds')}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Elastic Bandages</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">{t('staffMedicalEmergency.forSprainsAndStrains')}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Pain Relievers</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">Ibuprofen, acetaminophen</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Antihistamines</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">For allergic reactions</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-status-success-600">✓</span>
                <div>
                  <p className="font-semibold text-status-success-900 dark:text-status-success-200">Gloves & Masks</p>
                  <p className="text-status-success-700 dark:text-status-success-300 text-xs">Protection for responder</p>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200 mb-2">Common Procedures</h4>
            <ul className="space-y-2 text-status-success-800 dark:text-status-success-300">
              <li>
                <strong>Severe Bleeding:</strong> Apply direct pressure, elevate limb, use tourniquet if needed
              </li>
              <li>
                <strong>Choking:</strong> Perform Heimlich maneuver (abdominal thrusts)
              </li>
              <li>
                <strong>Shock:</strong> Lay flat, elevate legs, keep warm, monitor breathing
              </li>
              <li>
                <strong>Fracture/Sprain:</strong> RICE protocol (Rest, Ice, Compress, Elevate)
              </li>
            </ul>
          </div>

          <div className="bg-status-success-100 dark:bg-status-success-900/30 p-3 rounded border-l-4 border-status-success-600 mt-4">
            <p className="font-semibold text-status-success-900 dark:text-status-success-200">📍 First Aid Kit Locations:</p>
            <p className="text-status-success-700 dark:text-status-success-300 text-xs mt-1">
              See "First Aid Kit Locations" section above for staff-trained access points and supplies
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function GuidesTab() {
  return (
    <div className="space-y-6">
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6 mb-6">
        <h3 className="font-serif text-lg font-bold text-status-danger-900 dark:text-status-danger-200 flex items-center gap-2 mb-2">
          <AlertTriangle className="w-6 h-6" />
          Critical: Always Call 911 First
        </h3>
        <p className="text-status-danger-800 dark:text-status-danger-300">
          In any serious medical emergency, immediately call 911. These guides are supplementary tools
          while waiting for emergency responders. Professional medical care is always the priority.
        </p>
      </div>

      <CPRGuideSection />
      <AEDGuideSection />
      <FirstAidBasicsSection />
    </div>
  );
}
