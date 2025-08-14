#!/usr/bin/env python3
"""
Unit test using the ACTUAL asset file configuration that shows the expired contract issue.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path to import vortex modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vortex.models.future import Future
import pytz


def test_actual_gc_scenario():
    """Test with the ACTUAL asset file configuration: cycle = 'GJMQVZ'"""
    
    print("🚨 Testing ACTUAL GC Futures Scenario (Real Asset File)")
    print("=" * 65)
    
    # ACTUAL parameters from user's asset file
    instrument_code = "GC"
    futures_code = "GC"
    roll_cycle = "GJMQVZ"  # Feb, Apr, Jun, Aug, Oct, Dec - THE REAL CYCLE!
    tick_date = datetime(2008, 5, 4)
    days_count = 360  # Default from codebase
    
    # User's requested download range
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2025, 8, 10)
    
    print(f"📋 ACTUAL Parameters:")
    print(f"   Instrument: {instrument_code}")
    print(f"   Roll Cycle: {roll_cycle} (Feb, Apr, Jun, Aug, Oct, Dec)")
    print(f"   Download Range: {start_date.date()} to {end_date.date()}")
    print(f"   Days Count: {days_count}")
    print()
    
    # Generate futures contracts using the same logic as BaseDownloader
    print("🔄 Generating Futures Contracts with ACTUAL Cycle...")
    
    # Calculate extended end date (same as BaseDownloader logic)
    future_end_date = end_date + timedelta(days=days_count)
    print(f"   Extended end date: {future_end_date.date()} (original + {days_count} days)")
    print()
    
    # Generate year-month combinations
    contracts_generated = []
    current_date = start_date.replace(day=1)  # Start from beginning of month
    
    while current_date <= future_end_date:
        year = current_date.year
        month = current_date.month
        
        # Get month code for this month
        month_code = Future.get_code_for_month(month)
        print(f"   Checking {year}-{month:02d} -> Month code: {month_code}")
        
        # Check if this month code is in the roll cycle
        if month_code in roll_cycle:
            print(f"   ✅ Month {month_code} matches roll cycle '{roll_cycle}'")
            
            # Create the futures contract
            future_contract = Future(
                id=f"{futures_code}{month_code}{year}",
                futures_code=futures_code,
                year=year,
                month_code=month_code,
                tick_date=tick_date,
                days_count=days_count
            )
            
            # Get the contract's trading date range
            contract_start, contract_end = future_contract.get_date_range(tz=pytz.UTC)
            
            print(f"   📅 Contract {future_contract.symbol} trading range:")
            print(f"      Start: {contract_start.date()}")
            print(f"      End: {contract_end.date()}")
            
            # Check if this contract's range overlaps with our download request
            contract_start_date = contract_start.date()
            contract_end_date = contract_end.date()
            request_overlaps = not (end_date.date() < contract_start_date or start_date.date() > contract_end_date)
            
            # Also check if contract has already expired
            today = datetime.now().date()
            is_expired = contract_end_date < today
            
            if request_overlaps:
                if is_expired:
                    print(f"   ⚠️  Contract {future_contract.symbol} OVERLAPS but is EXPIRED! (ended {contract_end_date})")
                    print(f"       This explains the 'No data found' error!")
                else:
                    print(f"   ✅ Contract {future_contract.symbol} OVERLAPS and is ACTIVE")
                contracts_generated.append((future_contract, is_expired))
            else:
                print(f"   ❌ Contract {future_contract.symbol} does NOT overlap with download range")
        else:
            print(f"   ❌ Month {month_code} not in roll cycle '{roll_cycle}'")
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
        
        print()
    
    # Results
    print("📊 RESULTS:")
    print("=" * 40)
    
    if contracts_generated:
        print(f"✅ {len(contracts_generated)} contract(s) would be generated:")
        for contract, is_expired in contracts_generated:
            status = "🔴 EXPIRED" if is_expired else "🟢 ACTIVE"
            print(f"   📄 Contract: {contract.symbol} {status}")
            contract_start, contract_end = contract.get_date_range(tz=pytz.UTC)
            print(f"      Symbol: {contract.symbol}")
            print(f"      Trading Range: {contract_start.date()} to {contract_end.date()}")
            print(f"      Year: {contract.year}")
            print(f"      Month Code: {contract.month_code}")
            print(f"      Expected File: futures/1d/GC/GC_{contract.year}{contract.month:02d}.csv")
            if is_expired:
                print(f"      ⚠️  CONTRACT EXPIRED: This explains why Barchart returns no data!")
            print()
    else:
        print("❌ NO contracts would be generated!")
        print("   This means no downloads would occur.")
    
    return contracts_generated


def analyze_month_codes():
    """Show which months are in the GJMQVZ cycle"""
    print("\n📅 Month Code Analysis for GJMQVZ Cycle:")
    print("=" * 50)
    
    cycle = "GJMQVZ"
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    
    for month_num in range(1, 13):
        month_code = Future.get_code_for_month(month_num)
        month_name = month_names[month_num - 1]
        in_cycle = "✅ IN CYCLE" if month_code in cycle else "❌ NOT IN CYCLE"
        print(f"   {month_num:2d} ({month_name}) -> {month_code} {in_cycle}")


if __name__ == "__main__":
    try:
        # Show the cycle analysis first
        analyze_month_codes()
        
        # Run the actual scenario test
        contracts = test_actual_gc_scenario()
        
        # Summary
        print("\n🎯 EXPLANATION OF THE ISSUE:")
        print("=" * 60)
        
        if contracts:
            expired_contracts = [c for c, expired in contracts if expired]
            active_contracts = [c for c, expired in contracts if not expired]
            
            if expired_contracts:
                print("🚨 PROBLEM IDENTIFIED:")
                print(f"   - Vortex generated {len(expired_contracts)} EXPIRED contract(s)")
                print(f"   - Barchart correctly returns 'No data found' for expired contracts")
                print(f"   - The contract selection logic needs improvement!")
                print()
                
                for contract, _ in expired_contracts:
                    print(f"   EXPIRED: {contract.symbol} (ended {contract.get_date_range(pytz.UTC)[1].date()})")
            
            if active_contracts:
                print("✅ ACTIVE CONTRACTS FOUND:")
                for contract_tuple in active_contracts:
                    contract = contract_tuple[0]
                    print(f"   ACTIVE: {contract.symbol} (valid until {contract.get_date_range(pytz.UTC)[1].date()})")
        else:
            print("❌ No contracts generated!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()