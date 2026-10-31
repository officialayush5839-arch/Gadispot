# SmartPark Exchange — Mobile Screen Specifications & UX Requirements

> **Document Version:** 1.0.0  
> **Date:** 2026-10-31  
> **Platform:** Single Cross-Platform Flutter Mobile Application (Android & iOS)  
> **Audience:** Senior Flutter Architect, Mobile Engineers, UI/UX Designers  
> **Status:** Approved Engineering Specification  

---

## 1. Mobile Design Principles & Architectural Constraints

1. **Role-Based Dynamic Shell:** The application contains a single authentication entrypoint and dynamically renders Driver, Owner, or Guard navigation shells based on authenticated user claims.
2. **Defensive Mobile UX:** Every screen explicitly specifies 5 core states: **Loading**, **Populated**, **Empty**, **Error**, and **Offline/Degraded Network**.
3. **Hardware Capability Decoupling:** Location permissions, camera access, and push notifications implement graceful degradation workflows when permissions are denied.
4. **Zero Desktop Form Factors:** All views are mobile-native portrait interfaces optimized for one-handed thumb interaction.

---

## 2. Complete Screen Inventory by Role

### 2.1 Driver Role Screens (`SCR-100` Series)

```
[ SCR-001: Splash ] -> [ SCR-002: Phone Login ] -> [ SCR-003: OTP Verification ]
                                                            |
                                                            v
                                                  [ SCR-101: Explore Map/List ]
                                                            |
                                                            v
                                                  [ SCR-102: Space Details ]
                                                            |
                                                            v
                                                  [ SCR-103: Booking Checkout ]
                                                            |
                                                            v
                                                  [ SCR-104: Confirmed Pass & QR ]
                                                            |
                                                            v
                                                  [ SCR-105: Active Session ]
                                                            |
                                                            v
                                                  [ SCR-106: Completed & Rating ]
```

#### `SCR-101`: Driver Explore & Proximity Search
- **Role:** Driver.
- **Entry Point:** Application launch / Bottom Navigation Tab 1 ("Explore").
- **Core Elements:**
  - Full-screen Google Map with custom pin markers displaying hourly price badges (e.g., `₹40/hr`).
  - Floating top destination search bar with Google Places Autocomplete.
  - Floating filter bar: Time interval picker (`Arrival Time`, `Duration`), Vehicle Category selector pill (`Hatchback`, `Sedan`, `SUV`, `2-Wheeler`).
  - Bottom swipeable carousel of parking space summary cards synchronized with map pins.
- **States:**
  - *Loading:* Shimmer overlay across bottom carousel; map shows subtle pulsating blue location radius.
  - *Empty:* "No available spaces found within 3km. Try adjusting your arrival time or expanding search radius."
  - *Error:* Red snackbar with "Unable to fetch spaces. Tap to retry."
  - *Permission Denied (Location):* Map centers on default city center (e.g., MG Road, Bengaluru); banner prompts "Enable location for nearby parking."

#### `SCR-102`: Parking Bay Details & Restrictions
- **Role:** Driver.
- **Entry Point:** Tapping a space card or map pin in `SCR-101`.
- **Core Elements:**
  - High-resolution photo carousel: Entrance Gate, Exact Parking Bay, Approach Driveway.
  - Verification Badge: Green shield with "Property Authorization Verified".
  - Pricing Breakdown: Hourly rate, estimated total for selected window.
  - Amenity Badges: Covered / Open, CCTV Monitored, Gated Security, Guard on Duty.
  - Important Restrictions: Max height clearance (e.g., "2.1m Max Height - No Roof Racks"), No Commercial Taxis.
  - Cancellation Policy Summary: "Free cancellation up to 2 hours prior to arrival."
  - Fixed Bottom Sticky CTA: "Book This Bay - ₹[Total Amount]" (Navigates to `SCR-103`).

#### `SCR-103`: Booking Review & Hold Checkout
- **Role:** Driver.
- **Entry Point:** Tapping "Book This Bay" in `SCR-102`.
- **Core Elements:**
  - Top countdown banner: "Space held for 04:59. Complete payment to secure booking."
  - Time window summary card: Start date/time, End date/time, Total duration.
  - Vehicle selector: Dropdown of driver's registered vehicles or "Add Vehicle" shortcut.
  - Itemized Financial Breakdown:
    * Parking Base Fee (e.g., ₹80.00)
    * Platform Convenience Fee (₹10.00)
    * GST (18% on Convenience Fee: ₹1.80)
    * Total Driver Payable (₹91.80)
  - Bottom Primary Button: "Pay ₹91.80 via UPI" (Triggers Razorpay Flutter SDK).
- **Edge States:**
  - *Hold Expired (Timer hits 00:00):* Modal blocks screen: "Hold Expired: Your 5-minute reservation hold has expired. The space has been released. [Return to Search]".

#### `SCR-104`: Confirmed Booking & Dynamic Access Pass
- **Role:** Driver.
- **Entry Point:** Successful payment verification callback / Push notification / Tab 2 ("My Bookings").
- **Core Elements:**
  - High-contrast vector QR code generated via `qr_flutter` from server opaque token.
  - Arrival Countdown Widget: "Your reservation opens in 42 minutes."
  - Assigned Bay Callout: "BAY A-1 (Ground Floor Driveway)".
  - Vehicle Match Badge: "For Registered Vehicle: KA-01-AB-1234".
  - Quick Action Buttons:
    * "Navigate with Google Maps" (Launches external GPS intent).
    * "Report Arrival Issue / Gate Closed" (Triggers GPRP protocol `SCR-107`).
  - Caution Banner: "Keep your screen brightness high when presenting QR code to the guard."

#### `SCR-105`: Active Parking Session Tracker
- **Role:** Driver.
- **Entry Point:** Guard scans entry QR code / Push notification alert.
- **Core Elements:**
  - Circular progress timer showing elapsed time vs total reserved time.
  - Entry Timestamp: "Checked in at 13:52 by Guard Bahadur".
  - Scheduled Departure: "Exit by 16:00 (15-min grace window to 16:15)".
  - Prominent Action Button: "Extend Parking" (Re-queries availability; triggers extension checkout).
  - Overstay Warning Widget: Activates if time exceeds scheduled end: "Overstay Alert: 1.5x hourly rate applies after 16:15".

---

### 2.2 Space Owner Role Screens (`SCR-200` Series)

#### `SCR-201`: Space Owner Operations Dashboard
- **Role:** Space Owner.
- **Entry Point:** Owner Navigation Tab 1 ("Dashboard").
- **Core Elements:**
  - Real-Time Bay Occupancy Gauge: E.g., "2 of 3 Bays Currently Occupied".
  - Today's Revenue Widget: "Today's Gross: ₹480", "Net Payable: ₹398".
  - Quick Toggle: "Emergency Space Blackout" (Instantly blocks bay for personal use if unbooked).
  - Chronological list of expected arrivals and active parked vehicles.

#### `SCR-202`: Property Setup & Authorization Proof Uploader
- **Role:** Space Owner.
- **Entry Point:** Tab 2 ("My Properties") -> "Add Property".
- **Core Elements:**
  - Step 1: Property Name, Type (Driveway, Society, Commercial), Postal Address.
  - Step 2: Interactive map pin-dropper to capture exact latitude and longitude.
  - Step 3: Bay Scaffolding: Bay Label, Covered/Open, EV Charging, Vehicle Compatibility.
  - Step 4: Mandatory Legal Evidence Upload:
    * Document Type Selector (Tax Receipt, Sale Deed, Society NOC, Lease).
    * Camera/Gallery file picker (Uploads directly to private encrypted S3 bucket).
    * 3 Mandatory Photos: Entrance Gate, Parking Bay, Driveway Approach.
  - Submission Status Card: "Status: PENDING REVIEW (Audited within 24 hours)".

#### `SCR-203`: Owner Financial Ledger & Payout Settlement
- **Role:** Space Owner.
- **Entry Point:** Tab 4 ("Earnings").
- **Core Elements:**
  - Cumulative Un-disbursed Balance: E.g., "₹2,450.00 Ready for Next Payout".
  - Next Settlement Date: "Disbursing on Tuesday, Nov 4 via Direct IMPS".
  - Verified Bank Account Card: Bank Name, Masked Account (`****1234`), IFSC, Verification Status (Green Checkmark).
  - Itemized Ledger Transaction History: Date, Booking Ref, Gross Amount, Platform Fee (15%), Net Credited.

---

### 2.3 Security Guard Role Screens (`SCR-300` Series)

#### `SCR-301`: Guard Scanner Viewport
- **Role:** Guard.
- **Entry Point:** Guard Navigation Tab 1 ("Scan QR").
- **Core Elements:**
  - Full-screen camera viewfinder powered by `mobile_scanner`.
  - High-contrast visual bounding box with animated green laser scanning reticle.
  - Top Control Bar: Torch toggle (Flashlight on/off), Camera switch, Property Name.
  - Bottom Fallback CTA: "Enter Booking Reference Manually" (For cracked/unreadable driver screens).
- **Performance Requirement:** Sub-500ms barcode recognition; device vibration upon successful decode.

#### `SCR-302`: Scan Result Modal (Admit / Deny)
- **Role:** Guard.
- **Entry Point:** Triggered immediately upon decoding QR in `SCR-301`.
- **States:**
  - *SUCCESS (GREEN MODAL):*
    * Header: "ADMIT VEHICLE"
    * Big Bold Text: Assigned Bay Number (e.g., "BAY A-1")
    * Vehicle Plate: `KA-01-AB-1234`
    * Driver Name: Rohan Sharma
    * Valid Until: 16:00
    * Big Green Button: "Confirm Entry & Open Gate"
  - *REJECT (RED MODAL):*
    * Header: "ACCESS DENIED"
    * Reason Banner: "QR Already Used at 10:14 AM" OR "Pass Expired" OR "Wrong Property"
    * Action: "Dismiss"
  - *OBSTRUCTION FALLBACK:*
    * Secondary Red Outline Button: "Report Space Blocked" (Launches GPRP incident).

#### `SCR-303`: Today's Shift Schedule (Offline Cache)
- **Role:** Guard.
- **Entry Point:** Tab 2 ("Today's Schedule").
- **Core Elements:**
  - Pre-cached chronological list of expected arrivals for guard's 8-hour shift.
  - Search Bar: Quick search by last 4 digits of vehicle license plate.
  - Visual status pill: `EXPECTED`, `CHECKED_IN`, `COMPLETED`, `NO_SHOW`.
  - Manual Entry Button: Guard can verify physical vehicle plate and tap "Manual Admit" when network connectivity is dead in basements.

---

### 2.4 Platform Operations Role Screens (`SCR-400` Series)

#### `SCR-401`: Operations Mobile Verification Queue
- **Role:** Platform Operations / Admin.
- **Entry Point:** Role-restricted internal navigation view.
- **Core Elements:**
  - Filterable list of properties with `PENDING_REVIEW` authorization status.
  - Document Inspection Viewer: Secure zoomable view of uploaded property tax deeds and society NOCs.
  - Reviewer Action Panel:
    * "APPROVE LISTING" (Transitions property to `APPROVED`; spaces become bookable).
    * "REJECT LISTING" (Opens structured rejection reason modal: Document Illegible, Name Mismatch, Society NOC Missing).
- **Security Rule:** Mutating administrative approvals strictly require 2FA TOTP authentication.
